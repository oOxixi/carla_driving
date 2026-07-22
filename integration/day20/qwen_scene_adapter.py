from dataclasses import dataclass, asdict
from typing import List



@dataclass
class SceneObject:


    object_id:str

    object_type:str

    direction:str

    distance_m:float

    confidence:float

    risk:str



@dataclass
class SceneState:


    frame_id:int

    speed_kmh:float

    lane_id:int

    rain:float

    night:bool

    objects:List[SceneObject]



    def to_dict(self):

        return {


            "frame_id":
                self.frame_id,


            "ego":
            {
                "speed_kmh":
                    self.speed_kmh,

                "lane_id":
                    self.lane_id,
            },


            "weather":
            {
                "rain":
                    self.rain,

                "night":
                    self.night
            },


            "objects":
            [
                asdict(x)
                for x in self.objects
            ]
        }




def build_demo_scene():


    return SceneState(

        frame_id=100,


        speed_kmh=20,


        lane_id=1,


        rain=0.0,


        night=False,


        objects=[

            SceneObject(

                object_id="vehicle_001",

                object_type="vehicle",

                direction="front",

                distance_m=12.5,

                confidence=0.95,

                risk="medium"
            )
        ]

    )
