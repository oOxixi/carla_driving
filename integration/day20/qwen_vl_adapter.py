from __future__ import annotations


import torch
from PIL import Image

from transformers import (
    Qwen2_5_VLForConditionalGeneration,
    AutoProcessor,
)

from .qwen_prompt import build_decision_prompt


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
        scene_state,
    ):
        return build_decision_prompt(
            command_text=command_text,
            scene_state=scene_state,
        )



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
