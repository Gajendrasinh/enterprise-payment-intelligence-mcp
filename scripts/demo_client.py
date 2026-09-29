"""Interactive / CLI demonstration client for custom-payment-mcp server.

Connects to the server over stdio, executes each MCP function, and prints
formatted results for verification.
"""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")


def pretty(data: object) -> str:
    return json.dumps(data, indent=2)


async def main() -> None:
    print(f"{BOLD}{GREEN}Starting Payment MCP Server over stdio...{RESET}")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "payment_mcp.server"],
        env={"DEFAULT_ROLE": "ADMIN"},
    )

    async with (
        stdio_client(server_params) as (read, write),
        ClientSession(read, write) as session,
    ):
        # 1. Initialize
        init_res = await session.initialize()
        header("1. MCP Server Handshake")
        print(f"Server Name: {BOLD}{init_res.server_info.name}{RESET}")
        print(f"Protocol Version: {init_res.protocol_version}")

        # 2. List tools
        header("2. Discovered MCP Tools")
        tools = await session.list_tools()
        for t in tools.tools:
            print(f"  • {BOLD}{t.name}{RESET}: {t.description.splitlines()[0]}")

        # 3. Test get_payment_details
        header("3. Tool Test: get_payment_details('PAY-1001')")
        res_pay = await session.call_tool(
            "get_payment_details",
            {"payment_id": "PAY-1001"},
        )
        print(res_pay.content[0].text)  # type: ignore[union-attr]

        # 4. Test get_customer_details
        header("4. Tool Test: get_customer_details('CUS-001')")
        res_cus = await session.call_tool(
            "get_customer_details",
            {"customer_id": "CUS-001"},
        )
        print(res_cus.content[0].text)  # type: ignore[union-attr]

        # 5. Test find_customer_transactions
        header("5. Tool Test: find_customer_transactions('CUS-001', status='DECLINED')")
        res_tx = await session.call_tool(
            "find_customer_transactions",
            {"customer_id": "CUS-001", "status": "DECLINED"},
        )
        print(res_tx.content[0].text)  # type: ignore[union-attr]

        # 6. Test analyze_payment_risk (Medium & High Value)
        header("6. Tool Test: analyze_payment_risk('PAY-1001') [Declined < 1000]")
        res_risk1 = await session.call_tool(
            "analyze_payment_risk",
            {"payment_id": "PAY-1001"},
        )
        print(res_risk1.content[0].text)  # type: ignore[union-attr]

        header("6b. Tool Test: analyze_payment_risk('PAY-1003') [Declined >= 1000]")
        res_risk2 = await session.call_tool(
            "analyze_payment_risk",
            {"payment_id": "PAY-1003"},
        )
        print(res_risk2.content[0].text)  # type: ignore[union-attr]

        # 7. Test read_resource
        header("7. MCP Resource: policy://payment/decline-codes")
        policy = await session.read_resource("policy://payment/decline-codes")
        print(policy.contents[0].text)  # type: ignore[union-attr]

        # 8. Test get_prompt
        header("8. MCP Prompt: investigate_payment('PAY-1001')")
        prompt = await session.get_prompt(
            "investigate_payment",
            {"payment_id": "PAY-1001"},
        )
        print(prompt.messages[0].content.text)  # type: ignore[union-attr]

        print(f"\n{BOLD}{GREEN}✔ All MCP server capabilities verified successfully!{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
