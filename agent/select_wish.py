from typing import List
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition, RecognitionResult
from maa.context import Context


@AgentServer.custom_recognition("SelectHighestLevelWish")
class SelectHighestLevelWish(CustomRecognition):
    """
    Custom recognition that finds the highest level wish for a given type.

    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        wish_type = argv.custom_recognition_param
        print(f"[SelectHighestLevelWish] Received wish_type: {wish_type}")
        if (
            wish_type
            and len(wish_type) >= 2
            and wish_type[0] == wish_type[-1]
            and wish_type[0] in ("'", '"')
        ):
            wish_type = wish_type[1:-1]

        if not wish_type:
            print("[SelectHighestLevelWish] No wish type specified")
            return CustomRecognition.AnalyzeResult(
                box=None, detail="No wish type specified"
            )

        new_context = context.clone()

        # First, find all stage types on the page
        wishes_node = argv.node_name + "_" + wish_type
        wishes_detail = new_context.run_recognition(
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
            print(f"[SelectHighestLevelWish] Wish type '{wish_type}' not found on page")
            return CustomRecognition.AnalyzeResult(
                box=None, detail=f"Wish type '{wish_type}' not found"
            )

        print(
            f"[SelectHighestLevelWish] Found {len(wishes_detail.filterd_results)} wishes for type '{wish_type}'"
        )

        # Find the highest level dungeon for this stage type
        return self._find_highest_level_dungeon(
            new_context, argv, wishes_detail.filterd_results
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

        print(
            f"[SelectHighestLevelWish] Checking {len(wishes_recognitions)} wish recognitions for highest level"
        )
        for i, recognition in enumerate(wishes_recognitions):
            print(f"[SelectHighestLevelWish] Checking recognition {i}: {recognition}")
            if recognition.box is None or len(recognition.box) != 4:
                print(
                    f"[SelectHighestLevelWish] Recognition {i} has invalid box: {recognition.box}"
                )
                continue

            wish_node = argv.node_name + "_Level_" + str(i)
            print(
                f"[SelectHighestLevelWish] wish_node: {wish_node}, box: {recognition.box}"
            )
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
                print(
                    f"[SelectHighestLevelWish] wish_detail is None or has no best_result for node {wish_node}"
                )
                continue

            # Level is in the format of "Lv.55"
            wish_level_str = wish_detail.best_result.text
            print(f"[SelectHighestLevelWish] wish_level_str: {wish_level_str}")
            try:
                wish_level = int(wish_level_str.split(".")[1])
            except Exception as e:
                print(
                    f"[SelectHighestLevelWish] Failed to parse wish level from '{wish_level_str}': {e}"
                )
                continue

            print(f"[SelectHighestLevelWish] Parsed wish_level: {wish_level}")

            if wish_level < known_highest_level:
                print(
                    f"[SelectHighestLevelWish] wish_level {wish_level} < known_highest_level {known_highest_level}, skipping"
                )
                continue

            fulfilled_node = wish_node + "_Fulfilled"
            print(
                f"[SelectHighestLevelWish] Checking if wish is fulfilled at node: {fulfilled_node}"
            )
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
                print(
                    f"[SelectHighestLevelWish] Wish at node {fulfilled_node} is already fulfilled, skipping"
                )
                continue

            print(
                f"[SelectHighestLevelWish] New highest level found: {wish_level} at box {wish_detail.best_result.box}"
            )
            known_highest_level = wish_level
            known_highest_level_box = wish_detail.best_result.box

        if known_highest_level == -1:
            print("[SelectHighestLevelWish] No available dungeons found for stage type")
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail="No available dungeons found for stage type",
            )

        print(
            f"[SelectHighestLevelWish] Highest level dungeon found: {known_highest_level} at box {known_highest_level_box}"
        )
        return CustomRecognition.AnalyzeResult(
            box=known_highest_level_box,
            detail=f"Highest level dungeon found: {known_highest_level}",
        )
