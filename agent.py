# This file is part of Prometheus
# https://inl.gov/super-intelligence/prometheus/
#
# Copyright 2026 Battelle Energy Alliance, LLC
# All rights reserved, see NOTICE.txt for full restrictions
# https://github.com/idaholab/prometheus_core/blob/main/NOTICE.txt
#
# Licensed under the MIT License, please see LICENSE for details
# https://github.com/idaholab/prometheus_core/blob/main/LICENSE
#
# SPDX-License-Identifier: MIT

"""
Markdown to Plot Agent.

Identifies table from markdown based on user prompt and plots the requested data

This is a Prometheus specialist agent.  Subclass PrometheusAgent and implement
`_execute` — the base class handles the HTTP server, authentication, agent-card
serving, and registry registration for you.
"""

import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
from typing import Any
from pathlib import Path

from prometheus_api import load_prompt  # noqa: F401 - used by the LLM pattern below
from prometheus_api.agent import EventQueue, PrometheusAgent, RequestContext
from prometheus_api.llm_client import LLMConfig
from prometheus_api.storage_client.connection import ConnectionConfig

# Read secrets and configuration from environment variables.
# Never hard-code API keys or URLs here.
# Example (add `import os` to the imports above):
#   MY_API_KEY = os.getenv("MY_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MarkdownToPlotAgent(PrometheusAgent):
    """Markdown to Plot Agent."""

    async def _execute(
        self,
        params: dict[str, Any],
        context: RequestContext,
        event_queue: EventQueue,
    ) -> dict[str, Any]:

        if params["skill_id"] == "markdown_to_CSV":
            return await self.Extract_CSV(params,context,event_queue)
        if params["skill_id"] == "CSV_to_Plot":
                    return await self.Plot_CSV(params,context,event_queue)

    async def Plot_CSV(
            self,
            params: dict[str, Any],
            context: RequestContext,
            event_queue: EventQueue,
    ):
        """Process one request.

        Args:
            params: Parameters from the caller's JSON payload, plus ``skill_id``
                from the message metadata (the skill the orchestrator selected).
            context: The A2A request context.  Use ``context.context_id`` as a
                stable key for per-conversation state.
            event_queue: Pass to the ``send_*`` helpers to emit progress updates
                and artifacts.

        Returns:
            A plain ``dict``.  The base class wraps it as the final ``completed``
            task status automatically — do not enqueue that event yourself.
        """
        # ------------------------------------------------------------------
        # 1. Read inputs from params.  These keys must match the properties
        #    declared in agent_card.json's inputSchema.
        # ------------------------------------------------------------------

        document_ID = params.get("document_artifact_id")
        column_description = params.get("column_description")
        if not document_ID:
            return {"status": "error", "error": "Markdown file is not accessible"}
        if not column_description:
            return {"status": "error", "error": "Description of table to be searched for is missing."}
        cfg = LLMConfig.from_env()   # profile from .env
        if cfg.proxy_url:            # only the platform proxy
            cfg = cfg.with_api_key(os.getenv("LITELLM_MASTER_KEY"))

        # ------------------------------------------------------------------
        # 2. Send optional progress updates so the UI stays responsive.
        #    The base class sends the initial "working" update automatically;
        #    call this only when you want intermediate messages.
        # ------------------------------------------------------------------
        await self.send_status_update(
            context=context,
            event_queue=event_queue,
            message="Processing your request…",
        )

        # ------------------------------------------------------------------
        # 3. Do your actual work here.  Replace this with real logic.
        # ------------------------------------------------------------------
        path = await self.get_artifact_file_path(
            document_ID,
            context=context, artifacts=params.get("artifacts"))
        text = path.read_text()
        df = pd.read_csv(path)

        await self.send_status_update(
            context=context,
            event_queue=event_queue,
            message="Loading csv…",
        )

        async with self.llm_client(context, config=cfg) as llm:
            r = await llm.medium(
                f"Return ONLY the name of the column in '{df.columns}'? {column_description}")
        column_name = r.text

        # async with self.llm_client(context, config=cfg) as llm:
        #     r = await llm.medium(
        #         f"Return this table as a CSV file. It should be formatted as the raw text in a CSV file would be. Do not add any other text to your response. {table_text} ")
        # table_text = r.text

        plt.plot(df[column_name])

        # Save a local CSV file
        plt.savefig("plot.png")

        path = Path("plot.png").resolve()
        ref = await self.send_deeplynx_artifact(
            context=context, event_queue=event_queue,
            file_path=path, name="plot.png",
            description="Requested plot",
            storage_config=ConnectionConfig.from_env())

        result = {
            "status": "success",
            "input_received": True,
            "message": f"The user is looking for the plot :plot.png",
        }

        # ------------------------------------------------------------------
        # 4. Return a plain dict.  Keep keys consistent with the
        #    "output_format" you described in agent_card.json.
        # ------------------------------------------------------------------
        return result

    async def Extract_CSV(
                self,
                params: dict[str, Any],
                context: RequestContext,
                event_queue: EventQueue,
        ):
            """Process one request.
    
            Args:
                params: Parameters from the caller's JSON payload, plus ``skill_id``
                    from the message metadata (the skill the orchestrator selected).
                context: The A2A request context.  Use ``context.context_id`` as a
                    stable key for per-conversation state.
                event_queue: Pass to the ``send_*`` helpers to emit progress updates
                    and artifacts.
    
            Returns:
                A plain ``dict``.  The base class wraps it as the final ``completed``
                task status automatically — do not enqueue that event yourself.
            """
            # ------------------------------------------------------------------
            # 1. Read inputs from params.  These keys must match the properties
            #    declared in agent_card.json's inputSchema.
            # ------------------------------------------------------------------
    
            document_ID = params.get("document_artifact_id")
            table_description = params.get("table_description")
            if not document_ID:
                return {"status": "error", "error": "Markdown file is not accessible"}
            if not table_description:
                return {"status": "error", "error": "Description of table to be searched for is missing."}
            cfg = LLMConfig.from_env()   # profile from .env
            if cfg.proxy_url:            # only the platform proxy
                cfg = cfg.with_api_key(os.getenv("LITELLM_MASTER_KEY"))
    
            # ------------------------------------------------------------------
            # 2. Send optional progress updates so the UI stays responsive.
            #    The base class sends the initial "working" update automatically;
            #    call this only when you want intermediate messages.
            # ------------------------------------------------------------------
            await self.send_status_update(
                context=context,
                event_queue=event_queue,
                message="Processing your request…",
            )
    
            # ------------------------------------------------------------------
            # 3. Do your actual work here.  Replace this with real logic.
            # ------------------------------------------------------------------
            path = await self.get_artifact_file_path(
                document_ID,
                context=context, artifacts=params.get("artifacts"))
            text = path.read_text()
    
            await self.send_status_update(
                context=context,
                event_queue=event_queue,
                message="Locating table…",
            )
    
            async with self.llm_client(context, config=cfg) as llm:
                r = await llm.medium(
                    f"Return ONLY the table whose caption matches '{table_description}'? {text}")
            table_text = r.text
    
            async with self.llm_client(context, config=cfg) as llm:
                r = await llm.medium(
                    f"Return this table as a CSV file. It should be formatted as the raw text in a CSV file would be. Do not add any other text to your response. {table_text} ")
            table_text = r.text
    
            # Save a local CSV file
            with open("table.csv", "w") as file:
                file.write(table_text)
    
            path = Path("table.csv").resolve()
            ref = await self.send_deeplynx_artifact(
                context=context, event_queue=event_queue,
                file_path=path, name="table.csv",
                description="Requested table",
                storage_config=ConnectionConfig.from_env())
    
            result = {
                "status": "success",
                "input_received": True,
                "message": f"The user is looking for the table :{table_text}.",
            }
    
            # ------------------------------------------------------------------
            # 4. Return a plain dict.  Keep keys consistent with the
            #    "output_format" you described in agent_card.json.
            # ------------------------------------------------------------------
            return result

    # ----------------------------------------------------------------------
    # PATTERNS — uncomment and adapt as needed.
    # ----------------------------------------------------------------------
    #
    # Calling an LLM through the platform's LiteLLM gateway:
    #
    #     system_prompt = load_prompt("system_prompt.txt").format(input_data=input_data)
    #     async with self.llm_client(context) as llm:
    #         response = await llm.medium(system_prompt)
    #     return {"status": "success", "summary": response.text}
    #
    # Dispatching when agent_card.json declares more than one skill:
    #
    #     handler = {
    #         "skill_a": self._handle_a,
    #         "skill_b": self._handle_b,
    #     }.get(params.get("skill_id"))
    #     if handler is None:
    #         return {"status": "error", "error": f"Unknown skill: {params.get('skill_id')}"}
    #     return await handler(params, context, event_queue)
    #
    # Persisting per-conversation state across turns (Redis-backed, with an
    # in-memory fallback for local development):
    #
    #     state = self.load_context_state(str(context.context_id))
    #     state["count"] = state.get("count", 0) + 1
    #     self.save_context_state(str(context.context_id), state)
    #
    # See TUTORIAL.md ("Advanced topics") for emitting artifacts, asking the
    # user for missing inputs (INPUT_REQUIRED), and DeepLynx file storage.


if __name__ == "__main__":
    agent = MarkdownToPlotAgent(agent_name="Markdown to Plot Agent")
    agent.run()
