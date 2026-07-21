from __future__ import annotations

import json
import torch
from PIL import Image

from transformers import (
    Qwen2_5_VLForConditionalGeneration,
    AutoProcessor,
)


class QwenVLAdapter:


    def __init__(
        self,
        model_path="models/Qwen2.5-VL-7B"
    ):

        print(
            "Loading Qwen-VL:",
            model_path
        )


        self.processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=True
        )


        self.model = (
            Qwen2_5_VLForConditionalGeneration
            .from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            .eval()
        )



    def build_prompt(
        self,
        command_text,
        scene_state
    ):


        return f"""

你是自动驾驶行为决策模块。


你的任务:

融合:

1.驾驶员语音指令
2.RGB摄像头视觉信息
3.SceneState环境状态


输出车辆高层驾驶行为。


注意:

你不是车辆控制器。


禁止输出:

throttle

brake

steer


禁止输出:

方向盘

油门

刹车



只能输出:

START

STOP

SET_SPEED

TURN_LEFT

TURN_RIGHT

CHANGE_LANE_LEFT

CHANGE_LANE_RIGHT

AVOID_OBJECT

EMERGENCY_BRAKE

RETURN_TO_LANE



必须严格输出JSON。


格式:

{{
"actions":[
{{
"action":"",
"target_id":"",
"target_speed_kmh":0
}}
],
"confidence":0.0,
"reason":""
}}



视觉融合要求:

1.
必须检查RGB图像。

2.
必须结合SceneState。

3.
如果SceneState存在车辆，
但RGB没有观察到对应目标，
不要直接输出避障或跟车动作。

4.
reason必须说明视觉依据。



当前驾驶员指令:

{command_text}



当前SceneState:

{json.dumps(
scene_state,
ensure_ascii=False
)}



只输出JSON，不要解释。


"""




    def infer(
        self,
        command_text,
        scene_state,
        image_path=None
    ):


        prompt=self.build_prompt(
            command_text,
            scene_state
        )


        image=None


        content=[]


        if image_path:

            image=(
                Image.open(
                    image_path
                )
                .convert(
                    "RGB"
                )
            )


            content.append(
                {
                    "type":"image",
                    "image":image
                }
            )


        content.append(
            {
                "type":"text",
                "text":prompt
            }
        )



        messages=[
            {
                "role":"user",
                "content":content
            }
        ]



        text_prompt=(
            self.processor
            .apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        )



        if image is not None:

            inputs=self.processor(
                text=[text_prompt],
                images=[image],
                padding=True,
                return_tensors="pt"
            )

        else:

            inputs=self.processor(
                text=[text_prompt],
                padding=True,
                return_tensors="pt"
            )



        inputs={
            k:v.to(
                self.model.device
            )
            for k,v in inputs.items()
        }



        with torch.no_grad():

            output=self.model.generate(

                **inputs,

                max_new_tokens=256,

                do_sample=False

            )



        # =========================
        # 只取assistant生成部分
        # =========================


        input_len=(
            inputs["input_ids"]
            .shape[1]
        )


        generated_ids = (
            output[:,input_len:]
        )


        result=(
            self.processor
            .batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
        )



        print(
            "\n===== QWEN-VL JSON ====="
        )

        print(result)

        print(
            "========================"
        )



        return result
