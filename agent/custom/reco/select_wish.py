from typing import List
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition, RecognitionResult
from maa.context import Context
from utils import logger, parse_param


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

        # e.g. wish_type = "Credit/1", "Vanguard/2"
        wish_type = parse_param(argv.custom_recognition_param)
        logger.debug(f"[SelectHighestLevelWish] Received wish_type: {wish_type}")

        if not wish_type:
            logger.debug("[SelectHighestLevelWish] No wish type specified")
            return CustomRecognition.AnalyzeResult(
                box=None, detail="No wish type specified"
            )

        # ticket_number 1 = 3/3, 2 = 2/3, 3 = 1/3
        wish_type, ticket_number = wish_type.split(",")
        ticket_ocr_number = ticket_number

        if ticket_number == "1":
            ticket_ocr_number = "^3"
        elif ticket_number == "2":
            ticket_ocr_number = "^2"
        elif ticket_number == "3":
            ticket_ocr_number = "^1"

        new_context = context.clone()

        # First, find the ticket number on the page
        ticket_node = argv.node_name + "_" + ticket_number
        ticket_detail = new_context.run_recognition(
            ticket_node,
            argv.image,
            pipeline_override={
                ticket_node: {
                    "recognition": {
                        "type": "OCR",
                        "param": {
                            "expected": [ticket_ocr_number],
                            "roi": [1131, 116, 67, 41],
                        },
                    }
                }
            },
        )

        if ticket_detail is None or ticket_detail.best_result is None:
            logger.debug(
                f"[SelectHighestLevelWish] Ticket number '{ticket_number}' already used up"
            )
            context.override_pipeline({f"{argv.node_name}": {"enabled": False}})
            return CustomRecognition.AnalyzeResult(
                box=None, detail=f"Ticket number '{ticket_number}' already used up"
            )

        # Then, find all stage types on the page
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
            logger.debug(
                f"[SelectHighestLevelWish] Wish type '{wish_type}' not found on page"
            )
            return CustomRecognition.AnalyzeResult(
                box=None, detail=f"Wish type '{wish_type}' not found"
            )

        logger.debug(
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

        logger.debug(
            f"[SelectHighestLevelWish] Checking {len(wishes_recognitions)} wish recognitions for highest level"
        )
        for i, recognition in enumerate(wishes_recognitions):
            logger.debug(
                f"[SelectHighestLevelWish] Checking recognition {i}: {recognition}"
            )
            if recognition.box is None or len(recognition.box) != 4:
                logger.debug(
                    f"[SelectHighestLevelWish] Recognition {i} has invalid box: {recognition.box}"
                )
                continue

            wish_node = argv.node_name + "_Level_" + str(i)
            logger.debug(
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
                logger.debug(
                    f"[SelectHighestLevelWish] wish_detail is None or has no best_result for node {wish_node}"
                )
                continue

            # Level is in the format of "Lv.55"
            wish_level_str = wish_detail.best_result.text
            logger.debug(f"[SelectHighestLevelWish] wish_level_str: {wish_level_str}")
            try:
                wish_level = int(wish_level_str.split(".")[1])
            except Exception as e:
                logger.debug(
                    f"[SelectHighestLevelWish] Failed to parse wish level from '{wish_level_str}': {e}"
                )
                continue

            logger.debug(f"[SelectHighestLevelWish] Parsed wish_level: {wish_level}")

            if wish_level < known_highest_level:
                logger.debug(
                    f"[SelectHighestLevelWish] wish_level {wish_level} < known_highest_level {known_highest_level}, skipping"
                )
                continue

            fulfilled_node = wish_node + "_Fulfilled"
            logger.debug(
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
                logger.debug(
                    f"[SelectHighestLevelWish] Wish at node {fulfilled_node} is already fulfilled, skipping"
                )
                continue

            logger.debug(
                f"[SelectHighestLevelWish] New highest level found: {wish_level} at box {wish_detail.best_result.box}"
            )
            known_highest_level = wish_level
            known_highest_level_box = wish_detail.best_result.box

        if known_highest_level == -1:
            logger.debug(
                "[SelectHighestLevelWish] No available dungeons found for stage type"
            )
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail="No available dungeons found for stage type",
            )

        logger.debug(
            f"[SelectHighestLevelWish] Highest level dungeon found: {known_highest_level} at box {known_highest_level_box}"
        )
        return CustomRecognition.AnalyzeResult(
            box=known_highest_level_box,
            detail=f"Highest level dungeon found: {known_highest_level}",
        )
