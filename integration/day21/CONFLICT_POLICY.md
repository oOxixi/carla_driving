# Day21 Safety Conflict Policy


## Principle

Safety state has higher priority than user command.


Priority:


Safety

Qwen decision

User command



## Examples


### Red light


User:

继续走


Safety:

RED


Final:

STOP



### Pedestrian


User:

加速


Safety:

pedestrian detected


Final:

STOP



### Front vehicle risk


User:

保持速度


Safety:

TTC low


Final:

SET_SPEED or EMERGENCY_STOP



## Forbidden output


Danger scenario:


- START
- SPEED_UP


are forbidden.



## Interface


Final output:

VoiceCommandEnvelope


contains:

- schema_version
- command_id
- intent
- parameters
- confidence
- confirm_required

