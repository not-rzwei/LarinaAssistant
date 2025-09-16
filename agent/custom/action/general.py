from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from utils import logger


@AgentServer.custom_action("DisableNode")
class DisableNode(CustomAction):
    """
    将特定 node 设置为 disable 状态 。

    参数格式:
    {
        "node_name": "结点名称"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        node_name = argv.custom_action_param
        if (
            node_name
            and len(node_name) >= 2
            and node_name[0] == node_name[-1]
            and node_name[0] in ("'", '"')
        ):
            node_name = node_name[1:-1]

        logger.info(f"[DisableNode] Disabling node: {node_name}")
        context.override_pipeline({f"{node_name}": {"enabled": False}})

        return CustomAction.RunResult(success=True)
