#langchain chain
### from the graphstate, extract state and description. send it to supervisor prompt, send it to llm, get structured output and supervisor decision

import dotenv

from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from agents.supervisor.schema import SupervisorDecision
from agents.supervisor.prompt import supervisor_prompt
from graph.state import  Ticket


load_dotenv()
# os.getenv("GROQ_API_KEY")

class SupervisorAgent:
    """
    Langchain based Supervisor agent
    """

    def __init__(self):
        llm = ChatGroq(
            model="qwen/qwen3-32b",
            temperature = 0,
            max_retries=2
        )

        structured_llm = llm.with_structured_output(SupervisorDecision)

        self.chain = supervisor_prompt | structured_llm

    def invoke(self, ticket: Ticket) -> SupervisorDecision:
        """
        Invoke the Supervisor agent with the given ticket.

        Args:
            ticket (Ticket): The ticket to be processed by the Supervisor agent.

        Returns:
            SupervisorDecision: The structured decision made by the Supervisor agent.
        """
        # Prepare the input for the chain
        response = self.chain.invoke({
            "subject": ticket.subject,
            "description": ticket.description
        })

        # Run the chain and get the structured output

        return response