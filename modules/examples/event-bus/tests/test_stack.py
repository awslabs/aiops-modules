import aws_cdk as cdk
from aws_cdk.assertions import Template


def test_synthesize_stack() -> None:
    from event_bus import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    stack = stack.EventBusStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        event_bus_name="dummy123",
        source_accounts=["dummy123", "321dummy"],
        tags={"tag": "1"},
    )

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::Events::EventBus", 1)
