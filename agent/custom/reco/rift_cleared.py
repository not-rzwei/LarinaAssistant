import re
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from utils import logger, parse_rift_floor_number


@AgentServer.custom_recognition("RiftCleared")
class RiftCleared(CustomRecognition):
    """
    Custom recognition that checks if a rift is cleared by comparing
    the best floor number with the claimed floor number.
    Returns recognition result only if rift is not cleared (has unclaimed rewards).
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        node_name = argv.node_name
        roi = [argv.roi[0], argv.roi[1], argv.roi[2], argv.roi[3]]

        best_floor_node = node_name + "_BestFloor"
        best_floor_detail = context.run_recognition(
            best_floor_node,
            argv.image,
            pipeline_override={
                best_floor_node: {
                    "recognition": {
                        "type": "OCR",
                        "param": {
                            "expected": ["Floor"],
                            "roi": roi,
                        },
                    }
                }
            },
        )

        if best_floor_detail is None or best_floor_detail.best_result is None:
            logger.info(f"[{node_name}] Best floor not found.")
            return CustomRecognition.AnalyzeResult(
                box=None, detail="Best floor not found"
            )

        best_floor_text = best_floor_detail.best_result.text
        best_floor_number = self._parse_floor_number(best_floor_text)

        if best_floor_number is None:
            logger.info(
                f"[{node_name}] Could not parse best floor number from: {best_floor_text}"
            )
            return CustomRecognition.AnalyzeResult(
                box=None, detail="Could not parse best floor number"
            )

        claimed_floor_node = node_name + "_ClaimedFloor"
        claimed_floor_detail = context.run_recognition(
            claimed_floor_node,
            argv.image,
            pipeline_override={
                claimed_floor_node: {
                    "recognition": {
                        "type": "OCR",
                        "param": {
                            "expected": ["Claimed"],
                            "roi": roi,
                        },
                    }
                }
            },
        )

        if claimed_floor_detail is None or claimed_floor_detail.best_result is None:
            logger.info(f"[{node_name}] No claimed floor found")
            return CustomRecognition.AnalyzeResult(
                box=best_floor_detail.box, detail="Rift not cleared"
            )

        claimed_floor_number = parse_rift_floor_number(
            claimed_floor_detail.best_result.text
        )

        if claimed_floor_number is None:
            logger.info(
                f"[{node_name}] "
                f"Could not parse claimed floor number from: {claimed_floor_text}"
            )
            return CustomRecognition.AnalyzeResult(
                box=None, detail="Could not parse claimed floor number"
            )

        if claimed_floor_number < best_floor_number:
            logger.info(
                f"[{node_name}] Rift not cleared - Claimed {claimed_floor_number}F < Best {best_floor_number}F"
            )
            return CustomRecognition.AnalyzeResult(
                box=best_floor_detail.box,
                detail="Rift not cleared - has unclaimed rewards",
            )

        logger.info(f"[{node_name}] Rift is cleared")
        return CustomRecognition.AnalyzeResult(box=None, detail="Rift is cleared")

    def _parse_floor_number(self, text: str) -> int:
        """
        Parse floor number from text like "Floor 28" or "Floor X"
        Returns the number or None if not found
        """
        if not text:
            return None

        # Look for "Floor" followed by a number
        pattern = r"Floor\s*(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return int(match.group(1))

        return None


@AgentServer.custom_recognition("AllRiftCleared")
class AllRiftCleared(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        node_name = argv.node_name + "_ClaimedFloor"
        roi = [argv.roi[0], argv.roi[1], argv.roi[2], argv.roi[3]]

        detail = context.run_recognition(
            node_name,
            argv.image,
            pipeline_override={
                node_name: {
                    "recognition": {
                        "type": "OCR",
                        "param": {
                            "expected": ["Claimed"],
                            "roi": roi,
                        },
                    }
                }
            },
        )

        if detail is None or len(detail.filterd_results) < 5:
            logger.info(f"[{node_name}] All rifts are not cleared.")
            return CustomRecognition.AnalyzeResult(
                box=None, detail="All rifts are not cleared"
            )

        logger.info(f"[{node_name}] All rifts are cleared")
        return CustomRecognition.AnalyzeResult(
            box=detail.box, detail="All rifts are cleared"
        )
