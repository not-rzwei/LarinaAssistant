from enum import Enum
from typing import List
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import time

import numpy
from utils import logger


class Floor(Enum):
    I = "i"
    II = "ii"
    III = "iii"
    IV = "iv"


class BossInfo:
    def __init__(self, floors: List[Floor], recognition: List[str]):
        self.floors = floors
        self.recognition = recognition


bounty_map = {
    "Deity of Weaving": BossInfo(
        floors=[Floor.II, Floor.III, Floor.IV], recognition=["Weaving"]
    ),
    "Contractor of the Stem": BossInfo(
        floors=[Floor.II, Floor.III, Floor.IV], recognition=["Contractor"]
    ),
    "Skyrogue Mutant": BossInfo(floors=[Floor.III, Floor.IV], recognition=["Skyrogue"]),
    "Legionnaire Mutant": BossInfo(
        floors=[Floor.III, Floor.IV], recognition=["Legionnaire"]
    ),
    "Pyromancer Mutant": BossInfo(
        floors=[Floor.III, Floor.IV], recognition=["Pyromancer"]
    ),
    "Colossus Breaker": BossInfo(
        floors=[Floor.III, Floor.IV], recognition=["Colossus", "Breaker"]
    ),
    "Warped Orkean Sharpshooter": BossInfo(
        floors=[Floor.III, Floor.IV], recognition=["Warped Orkean", "Sharpshooter"]
    ),
    "Frost Orb": BossInfo(floors=[Floor.III, Floor.IV], recognition=["Frost", "Orb"]),
    "Deity of Thunder": BossInfo(
        floors=[Floor.III, Floor.IV], recognition=["Deity", "Thunder"]
    ),
    "Shadow Knight": BossInfo(
        floors=[Floor.III, Floor.IV], recognition=["Shadow", "Knight"]
    ),
    "Shade Of False Dreams": BossInfo(
        floors=[Floor.III, Floor.IV], recognition=["Shade", "False", "Dreams"]
    ),
}


@AgentServer.custom_recognition("SelectBounty")
class SelectBounty(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        bounty_name = argv.custom_recognition_param
        logger.debug(f"[SelectBounty] Received bounty_name: {bounty_name}")
        if (
            bounty_name
            and len(bounty_name) >= 2
            and bounty_name[0] == bounty_name[-1]
            and bounty_name[0] in ("'", '"')
        ):
            bounty_name = bounty_name[1:-1]
            logger.debug(
                f"[SelectBounty] Stripped quotes from bounty_name: {bounty_name}"
            )

        node_name = argv.node_name + "_" + bounty_name
        logger.debug(f"[SelectBounty] node_name: {node_name}")
        bounty_info = bounty_map[bounty_name]
        logger.debug(
            f"[SelectBounty] bounty_info: floors={bounty_info.floors}, recognition={bounty_info.recognition}"
        )

        # select the higest floor available, if none is available, select the lowest floor
        highest_floor = None
        for floor in bounty_info.floors:
            floor_node_name = node_name + "_" + floor.value
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
                                    "stage/bounty-floor-" + floor.value + ".png"
                                ],
                                "order_by": "Score",
                            },
                        },
                    }
                },
            )

            if floor_detail is None or floor_detail.box is None:
                continue

            highest_floor = floor_detail

        if highest_floor is None:
            logger.debug("[SelectBounty] No floor found")
            return CustomRecognition.AnalyzeResult(box=None, detail="No floor found")

        logger.debug(f"[SelectBounty] Floor found at: {highest_floor.box}")
        click_floor_job = context.tasker.controller.post_click(
            highest_floor.box.x, highest_floor.box.y
        )
        click_floor_job.wait()
        logger.debug("[SelectBounty] Clicked floor, waiting for boss selection...")

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
                logger.debug("[SelectBounty] Screencap failed, retrying...")
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
                logger.debug(f"[SelectBounty] Boss found at: {boss_detail.box}")
                return CustomRecognition.AnalyzeResult(
                    box=boss_detail.box, detail="Boss selected"
                )

            logger.debug("[SelectBounty] Boss not found, swiping to next...")
            swipe_job = context.tasker.controller.post_swipe(1100, 400, 350, 400, 1000)
            swipe_job.wait()

        logger.debug("[SelectBounty] Bounty not found after timeout")
        return CustomRecognition.AnalyzeResult(box=None, detail="Bounty not found")
