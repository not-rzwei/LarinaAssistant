from typing import List
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition, RecognitionResult
from maa.context import Context


@AgentServer.custom_recognition("CheckShopItem")
class CheckShopItem(CustomRecognition):
    """
    Custom recognition that checks if a shop item is available for purchase.
    Returns recognition result only if item is found AND not sold out.
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        item_name = argv.custom_recognition_param
        if (
            item_name
            and len(item_name) >= 2
            and item_name[0] == item_name[-1]
            and item_name[0] in ("'", '"')
        ):
            item_name = item_name[1:-1]

        node_name = argv.node_name + "_" + item_name
        reco_detail = context.run_recognition(
            node_name,
            argv.image,
            pipeline_override={
                node_name: {
                    "recognition": {
                        "type": "OCR",
                        "param": {"expected": [item_name]},
                        "timeout": 10000,
                    }
                }
            },
        )

        if reco_detail == None:
            return CustomRecognition.AnalyzeResult(
                box=None, detail="Item not available"
            )

        item_box = reco_detail.box
        sold_out_roi = [
            item_box.x,
            item_box.y - 50,
            max(item_box.w + 50, 150),
            max(item_box.h + 50, 70),
        ]
        sold_out_node = node_name + "_SoldOut"
        sold_out_detail = context.run_recognition(
            sold_out_node,
            argv.image,
            pipeline_override={
                sold_out_node: {
                    "recognition": {
                        "type": "OCR",
                        "param": {
                            "expected": ["Sold Out", "sold out", "sold", "Sold"],
                            "roi": sold_out_roi,
                        },
                        "timeout": 10000,
                    }
                }
            },
        )

        if sold_out_detail is not None:
            return CustomRecognition.AnalyzeResult(box=None, detail="Item sold out")

        return CustomRecognition.AnalyzeResult(
            box=reco_detail.box, detail="Item available"
        )


@AgentServer.custom_recognition("SelectHighestLevelWish")
class SelectHighestLevelDungeon(CustomRecognition):
    """
    Custom recognition that finds the highest level wish for a given type.

    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        wish_type = argv.custom_recognition_param
        if (
            wish_type
            and len(wish_type) >= 2
            and wish_type[0] == wish_type[-1]
            and wish_type[0] in ("'", '"')
        ):
            wish_type = wish_type[1:-1]

        if not wish_type:
            return CustomRecognition.AnalyzeResult(
                box=None, detail="No wish type specified"
            )

        # First, find all stage types on the page
        wishes_node = argv.node_name + "_" + wish_type
        wishes_detail = context.run_recognition(
            wishes_node,
            argv.image,
            pipeline_override={
                wishes_node: {
                    "recognition": {
                        "type": "OCR",
                        "param": {
                            "expected": [wish_type],
                            "roi": [141, 90, 1101, 598],
                        },
                    }
                }
            },
        )

        if wishes_detail is None or len(wishes_detail.filterd_results) == 0:
            return CustomRecognition.AnalyzeResult(
                box=None, detail=f"Wish type '{wish_type}' not found"
            )

        # Find the highest level dungeon for this stage type
        return self._find_highest_level_dungeon(
            context, argv, wishes_detail.filterd_results
        )

    def _find_highest_level_dungeon(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
        wishes_recognitions: List[RecognitionResult],
    ) -> CustomRecognition.AnalyzeResult:
        """
        Find the highest level available dungeon for the given stage type.
        """
        known_highest_level = -1
        known_highest_level_box = None

        for i, recognition in enumerate(wishes_recognitions):
            if recognition.box is None or len(recognition.box) != 4:
                continue

            wish_node = argv.node_name + "_Level_" + str(i)
            wish_detail = context.run_recognition(
                wish_node,
                argv.image,
                pipeline_override={
                    wish_node: {
                        "recognition": {
                            "type": "OCR",
                            "param": {
                                "expected": ["^.+[0-9]+$"],
                                "roi": [
                                    recognition.box[0],
                                    recognition.box[1] - 30,
                                    recognition.box[2] + 10,
                                    recognition.box[3] + 40,
                                ],
                            },
                        },
                    },
                },
            )

            if wish_detail is None or wish_detail.best_result is None:
                continue

            # Level is in the format of "Lv.55"
            wish_level_str = wish_detail.best_result.text
            wish_level = int(wish_level_str.split(".")[1])

            if wish_level < known_highest_level:
                continue

            fulfilled_node = wish_node + "_Fulfilled"
            fulfilled_detail = context.run_recognition(
                fulfilled_node,
                argv.image,
                pipeline_override={
                    fulfilled_node: {
                        "recognition": {
                            "type": "OCR",
                            "param": {
                                "expected": ["Wish", "Fulfilled", "filled"],
                                "roi": [
                                    recognition.box[0] + 60,
                                    recognition.box[1] - 30,
                                    recognition.box[2] + 60,
                                    recognition.box[3] + 30,
                                ],
                            },
                        },
                    },
                },
            )

            if fulfilled_detail is not None:
                continue

            known_highest_level = wish_level
            known_highest_level_box = wish_detail.best_result.box

        if known_highest_level == -1:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail="No available dungeons found for stage type",
            )

        return CustomRecognition.AnalyzeResult(
            box=known_highest_level_box,
            detail=f"Highest level dungeon found: {known_highest_level}",
        )
