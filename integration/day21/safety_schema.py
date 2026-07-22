from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional



@dataclass
class SafetyStateSummary:
    """
    Day21 Safety State Interface

    接收第二组:
        LiDAR摘要
        安全状态摘要

    提供给:
        Qwen多模态决策

    """

    schema_version:str="1.0"


    # traffic safety

    traffic_light:str="UNKNOWN"


    # lidar summary

    lidar_object_count:int=0


    nearest_object_distance_m:Optional[float]=None


    # pedestrian / obstacle

    pedestrian_risk:bool=False


    obstacle_risk:bool=False



    # TTC

    ttc_s:Optional[float]=None



    # vehicle dynamics

    front_distance_m:float=999.0


    closing_speed_mps:float=0.0



    # environment

    weather:str="clear"



    # confidence

    input_confidence:float=1.0



    recommended_action:str="NONE"



    def to_dict(self):

        return asdict(self)
