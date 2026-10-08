// J6/nash-p UCP API. No mock, no ONNX fallback, no hbDNN v1 API.
#include "hobot/dnn/hb_dnn.h"
#include "hobot/hb_ucp.h"
#include "hobot/hb_ucp_sys.h"
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

using Shape = std::vector<int>;
static const std::map<std::string, Shape> kInputs = {
  {"rgb", {1,3,224,224}}, {"text_tokens", {1,32}},
  {"targets", {1,8,14}}, {"state", {1,64}}};
static const std::map<std::string, Shape> kOutputs = {
  {"plan_length_logits",{1,4}}, {"behavior_logits",{1,4,14}},
  {"target_pointer_logits",{1,4,9}}, {"target_lane_logits",{1,4,6}},
  {"target_speed_mps",{1,4}}, {"completion_type_logits",{1,4,8}},
  {"on_failure_logits",{1,4,4}}, {"confidence",{1,1}},
  {"requires_confirmation_logits",{1,1}}, {"replan_condition_logits",{1,7}}};
static void check(int status, const char* operation) {
  if (status != 0) throw std::runtime_error(std::string(operation)+" status="+std::to_string(status));
}
static int64_t now_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
}
static size_t count(const hbDNNTensorProperties& p) {
  size_t n=1;
  for(int d=0;d<p.validShape.numDimensions;++d) n*=p.validShape.dimensionSize[d];
  return n;
}
// Flattened canonical tensor coordinates -> SDK byte offset. Padding is never
// interpreted as output; each valid element is visited using SDK byte strides.
static size_t offset(size_t linear, const hbDNNTensorProperties& p) {
  size_t result=0;
  for(int d=p.validShape.numDimensions-1;d>=0;--d) {
    const size_t dim=static_cast<size_t>(p.validShape.dimensionSize[d]);
    result+=(linear%dim)*static_cast<size_t>(p.stride[d]); linear/=dim;
  }
  return result;
}
class Runtime {
  hbDNNPackedHandle_t packed_=nullptr;
  hbDNNHandle_t model_=nullptr;
  std::vector<hbDNNTensor> inputs_, outputs_;
  std::vector<std::string> input_names_, output_names_;
  std::string name_;
  void cleanup() noexcept {
    for(auto& t: inputs_) if(t.sysMem.virAddr) hbUCPFree(&t.sysMem);
    for(auto& t: outputs_) if(t.sysMem.virAddr) hbUCPFree(&t.sysMem);
    if(packed_) hbDNNRelease(packed_);
    packed_=nullptr;
  }
  void prepare(bool input) {
    int n=0;
    check(input?hbDNNGetInputCount(&n,model_):hbDNNGetOutputCount(&n,model_),"GetCount");
    const auto& expected=input?kInputs:kOutputs;
    if(n!=static_cast<int>(expected.size())) throw std::runtime_error("Tensor count mismatch");
    auto& ts=input?inputs_:outputs_; auto& names=input?input_names_:output_names_;
    ts.resize(n); std::map<std::string,bool> seen;
    for(int i=0;i<n;++i) {
      const char* name=nullptr;
      check(input?hbDNNGetInputName(&name,model_,i):hbDNNGetOutputName(&name,model_,i),"GetName");
      if(!name || !expected.count(name) || seen[name]) throw std::runtime_error("Unknown/duplicate tensor name");
      seen[name]=true; names.emplace_back(name);
      auto& p=ts[i].properties;
      check(input?hbDNNGetInputTensorProperties(&p,model_,i):hbDNNGetOutputTensorProperties(&p,model_,i),"GetProperties");
      const auto& shape=expected.at(name);
      if(p.validShape.numDimensions!=static_cast<int>(shape.size())) throw std::runtime_error("Rank mismatch: "+names.back());
      for(size_t d=0;d<shape.size();++d) {
        if(p.validShape.dimensionSize[d]!=shape[d] || p.stride[d]<=0)
          throw std::runtime_error("Shape/dynamic stride unsupported: "+names.back());
      }
      // This bridge expects float featuremap external I/O. Internal
      // INT8 BPU arithmetic is independent of external tensor element type.
      // Refuse other external types rather than silently misquantizing them.
      if(p.tensorType!=HB_DNN_TENSOR_TYPE_F32 || p.quantiType!=NONE)
        throw std::runtime_error("Requires external float32/NONE tensor: "+names.back());
      if(p.alignedByteSize<=0 || p.stride[shape.size()-1]<4 ||
         offset(count(p)-1,p)+4>static_cast<size_t>(p.alignedByteSize))
        throw std::runtime_error("Invalid stride/allocation size: "+names.back());
      check(hbUCPMallocCached(&ts[i].sysMem,p.alignedByteSize,0),"hbUCPMallocCached");
    }
  }
public:
  explicit Runtime(const std::string& file, const std::string& requested) {
    try {
      const char* path=file.c_str();
      check(hbDNNInitializeFromFiles(&packed_,&path,1),"hbDNNInitializeFromFiles");
      const char** names=nullptr; int n=0;
      check(hbDNNGetModelNameList(&names,&n,packed_),"hbDNNGetModelNameList");
      if(n<1 || (requested.empty() && n!=1)) throw std::runtime_error("Specify model name for multi-model HBM");
      name_=requested.empty()?names[0]:requested;
      check(hbDNNGetModelHandle(&model_,packed_,name_.c_str()),"hbDNNGetModelHandle");
      prepare(true); prepare(false);
    } catch(...) {cleanup(); throw;}
  }
  Runtime(const Runtime&)=delete;
  Runtime& operator=(const Runtime&)=delete;
  ~Runtime() {cleanup();}
  void describe() const {
    // Tensor names belong to the fixed contract and therefore need no escaping.
    std::cout<<"{\"backend\":\"hbDNNInferV2/UCP\",\"resident\":true,\"external_dtype\":\"float32\",\"inputs\":[";
    describe_tensors(inputs_,input_names_);
    std::cout<<"],\"outputs\":["; describe_tensors(outputs_,output_names_); std::cout<<"]}\n";
  }
  static void describe_tensors(const std::vector<hbDNNTensor>& ts,const std::vector<std::string>& names) {
    for(size_t i=0;i<ts.size();++i) {
      if(i) std::cout<<",";
      const auto& p=ts[i].properties;
      std::cout<<"{\"name\":\""<<names[i]<<"\",\"shape\":[";
      for(int d=0;d<p.validShape.numDimensions;++d) {if(d) std::cout<<","; std::cout<<p.validShape.dimensionSize[d];}
      std::cout<<"],\"stride_bytes\":[";
      for(int d=0;d<p.validShape.numDimensions;++d) {if(d) std::cout<<","; std::cout<<p.stride[d];}
      std::cout<<"],\"aligned_bytes\":"<<p.alignedByteSize<<"}";
    }
  }
  void run(const std::filesystem::path& in, const std::filesystem::path& out) {
    for(size_t i=0;i<inputs_.size();++i) {
      auto& t=inputs_[i]; const size_t n=count(t.properties);
      auto path=in/(input_names_[i]+".f32");
      if(std::filesystem::file_size(path)!=n*4) throw std::runtime_error("Input size mismatch: "+path.string());
      std::vector<float> values(n); std::ifstream f(path,std::ios::binary);
      if(!f.read(reinterpret_cast<char*>(values.data()),n*4)) throw std::runtime_error("Input read failed");
      std::memset(t.sysMem.virAddr,0,static_cast<size_t>(t.properties.alignedByteSize));
      for(size_t j=0;j<n;++j) {
        if(!std::isfinite(values[j])) throw std::runtime_error("Non-finite input");
        std::memcpy(static_cast<char*>(t.sysMem.virAddr)+offset(j,t.properties),&values[j],4);
      }
      check(hbUCPMemFlush(&t.sysMem,HB_SYS_MEM_CACHE_CLEAN),"input CLEAN");
    }
    hbUCPTaskHandle_t task=nullptr;
    const int64_t start=now_ns();
    try {
      check(hbDNNInferV2(&task,outputs_.data(),inputs_.data(),model_),"hbDNNInferV2");
      hbUCPSchedParam schedule;
      HB_UCP_INITIALIZE_SCHED_PARAM(&schedule);
      schedule.backend=HB_UCP_BPU_CORE_ANY;
      check(hbUCPSubmitTask(task,&schedule),"hbUCPSubmitTask");
      // 0 waits until completion: do not free DMA memory with a task in flight.
      check(hbUCPWaitTaskDone(task,0),"hbUCPWaitTaskDone");
    } catch(...) {
      if(task) hbUCPReleaseTask(task);
      throw;
    }
    const int64_t end=now_ns();
    const int released=hbUCPReleaseTask(task); task=nullptr;
    check(released,"hbUCPReleaseTask");
    std::filesystem::create_directories(out);
    for(size_t i=0;i<outputs_.size();++i) {
      auto& t=outputs_[i]; check(hbUCPMemFlush(&t.sysMem,HB_SYS_MEM_CACHE_INVALIDATE),"output INVALIDATE");
      std::vector<float> values(count(t.properties));
      for(size_t j=0;j<values.size();++j) {
        std::memcpy(&values[j],static_cast<char*>(t.sysMem.virAddr)+offset(j,t.properties),4);
        if(!std::isfinite(values[j])) throw std::runtime_error("Non-finite output");
      }
      std::ofstream f(out/(output_names_[i]+".f32"),std::ios::binary|std::ios::trunc);
      if(!f.write(reinterpret_cast<const char*>(values.data()),values.size()*4)) throw std::runtime_error("Output write failed");
      f.close();
      if(!f) throw std::runtime_error("Output close failed");
    }
    std::cout<<"OK\t"<<start<<"\t"<<end<<std::endl;
  }
};
int main(int argc,char** argv) {
  try {
    if(argc<3) throw std::runtime_error("Usage: student_hbdnn MODEL.hbm --describe|--worker [MODEL_NAME]");
    Runtime runtime(argv[1],argc>3?argv[3]:"");
    std::string mode=argv[2];
    if(mode=="--describe") {runtime.describe(); return 0;}
    if(mode!="--worker") throw std::runtime_error("Unknown mode");
    std::cout<<"READY"<<std::endl;
    std::string line;
    while(std::getline(std::cin,line)) {
      if(line=="QUIT") break;
      const auto a=line.find('\t'), b=line.find('\t',a==std::string::npos?0:a+1);
      if(a==std::string::npos || b==std::string::npos || line.substr(0,a)!="RUN" || line.find('\t',b+1)!=std::string::npos)
        throw std::runtime_error("Worker expects RUN<TAB>input_dir<TAB>output_dir");
      runtime.run(line.substr(a+1,b-a-1),line.substr(b+1));
    }
    return 0;
  } catch(const std::exception& e) {
    std::cerr<<"student_hbdnn: "<<e.what()<<std::endl; return 1;
  }
}
