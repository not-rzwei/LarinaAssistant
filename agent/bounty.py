from enum import Enum
from typing import List
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import time

import numpy


class Floor(Enum):
    I = "i"
    II = "ii"
    III = "iii"
    IV = "iv"


class BossInfo:
    def __init__(self, floors: Floor, recognition: List[str]):
        self.floors = floors
        self.recognition = recognition


bounty_map = {
    "Shade Of False Dreams IV": BossInfo(floors=Floor.IV, recognition=["Shade"]),
}


@AgentServer.custom_recognition("SelectBounty")
class SelectBounty(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        bounty_name = argv.custom_recognition_param
        print(f"[SelectBounty] Received bounty_name: {bounty_name}")
        if (
            bounty_name
            and len(bounty_name) >= 2
            and bounty_name[0] == bounty_name[-1]
            and bounty_name[0] in ("'", '"')
        ):
            bounty_name = bounty_name[1:-1]
            print(f"[SelectBounty] Stripped quotes from bounty_name: {bounty_name}")

        node_name = argv.node_name + "_" + bounty_name
        print(f"[SelectBounty] node_name: {node_name}")
        bounty_info = bounty_map[bounty_name]
        print(
            f"[SelectBounty] bounty_info: floors={bounty_info.floors}, recognition={bounty_info.recognition}"
        )

        # select floor
        floor_node_name = node_name + "_" + str(bounty_info.floors)
        print(f"[SelectBounty] floor_node_name: {floor_node_name}")
        floor_detail = context.run_recognition(
            floor_node_name,
            argv.image,
            pipeline_override={
                floor_node_name: {
                    "recognition": {
                        "type": "TemplateMatch",
                        "param": {
                            "roi": [0, 185, 214, 483],
                            "template": [
                                "stage/bounty-floor-"
                                + bounty_info.floors.value
                                + ".png"
                            ],
                            "order_by": "Score",
                        },
                    },
                }
            },
        )

        if floor_detail == None:
            print("[SelectBounty] Floor not found")
            return CustomRecognition.AnalyzeResult(box=None, detail="Floor not found")

        print(f"[SelectBounty] Floor found at: {floor_detail.box}")
        click_floor_job = context.tasker.controller.post_click(
            floor_detail.box.x, floor_detail.box.y
        )
        click_floor_job.wait()
        print("[SelectBounty] Clicked floor, waiting for boss selection...")

        # select boss
        start_time = time.time()
        timeout = 10  # seconds

        boss_detail = None

        while time.time() - start_time < timeout:
            time.sleep(1)
            screencap_job = context.tasker.controller.post_screencap()
            screencap_job.wait()
            image = screencap_job.get()

            if image is None or numpy.array(image).size == 0:
                print("[SelectBounty] Screencap failed, retrying...")
                continue

            boss_detail = context.run_recognition(
                node_name,
                image,
                pipeline_override={
                    node_name: {
                        "recognition": {
                            "type": "OCR",
                            "param": {"expected": bounty_info.recognition},
                        },
                    }
                },
            )

            if boss_detail is not None and boss_detail.box is not None:
                print(f"[SelectBounty] Boss found at: {boss_detail.box}")
                return CustomRecognition.AnalyzeResult(
                    box=boss_detail.box, detail="Boss selected"
                )

            print("[SelectBounty] Boss not found, swiping to next...")
            swipe_job = context.tasker.controller.post_swipe(1100, 400, 350, 400, 1000)
            swipe_job.wait()

        print("[SelectBounty] Bounty not found after timeout")
        return CustomRecognition.AnalyzeResult(box=None, detail="Bounty not found")
