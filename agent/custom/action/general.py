from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from utils import logger, parse_param


@AgentServer.custom_action("DisableNode")
class DisableNode(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        node_name = parse_param(argv.custom_action_param)

        logger.debug(f"[DisableNode] Disabling node: {node_name}")
        context.override_pipeline({f"{node_name}": {"enabled": False}})

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("StopAllTasks")
class StopAllTasks(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        job = context.tasker.post_stop()
        job.wait()
        return CustomAction.RunResult(success=True)
