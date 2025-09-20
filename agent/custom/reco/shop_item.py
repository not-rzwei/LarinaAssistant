from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context


from utils import logger


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

        parent_node_name = argv.node_name
        roi = [argv.roi[0], argv.roi[1], argv.roi[2], argv.roi[3]]
        node_name = argv.node_name + "_" + item_name
        reco_detail = context.run_recognition(
            node_name,
            argv.image,
            pipeline_override={
                node_name: {
                    "recognition": {
                        "type": "OCR",
                        "param": {"expected": [item_name], "roi": roi},
                        "timeout": 10000,
                    }
                }
            },
        )

        if reco_detail is None:
            logger.debug(f"[CheckShopItem] Item '{item_name}' not found.")
            return CustomRecognition.AnalyzeResult(
                box=None, detail="Item not available"
            )

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
                            "roi": roi,
                        },
                        "timeout": 10000,
                    }
                }
            },
        )

        if sold_out_detail is not None:
            logger.debug(f"[CheckShopItem] Item '{item_name}' is sold out.")
            context.override_pipeline({f"{parent_node_name}": {"enabled": False}})
            return CustomRecognition.AnalyzeResult(box=None, detail="Item sold out")

        logger.debug(f"[CheckShopItem] Item '{item_name}' is available for purchase.")
        return CustomRecognition.AnalyzeResult(
            box=reco_detail.box, detail="Item available"
        )
