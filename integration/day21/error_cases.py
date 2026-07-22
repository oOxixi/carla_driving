ERROR_CASES=[


{
"type":"format_error",
"problem":
"Qwen输出markdown而不是JSON",
"solution":
"parser提取JSON"
},


{
"type":"wrong_action",
"problem":
"危险场景输出START",
"solution":
"Safety优先覆盖"
},


{
"type":"low_confidence",
"problem":
"confidence过低仍执行",
"solution":
"requires_confirmation"
},


{
"type":"safety_conflict",
"problem":
"用户要求加速但红灯",
"solution":
"STOP"
},


{
"type":"vision_missing",
"problem":
"RGB漏检目标",
"solution":
"SafetyState兜底"

}

]
