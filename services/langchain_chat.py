"""LangChain message pipeline for the configured NVIDIA chat endpoint."""
import os

from langchain_core.runnables import RunnableLambda


ROLES = {'system': 'system', 'human': 'user', 'ai': 'assistant'}


def chat_chain(prompt, provider, *, max_tokens):
    async def request(prompt_value):
        messages = [
            {'role': ROLES[message.type], 'content': message.content}
            for message in prompt_value.to_messages()
        ]
        return await provider('/chat/completions', {
            'model': os.getenv('NVIDIA_CHAT_MODEL'),
            'messages': messages,
            'temperature': 0.1,
            'max_tokens': max_tokens,
            'chat_template_kwargs': {'enable_thinking': False},
            'response_format': {'type': 'json_object'},
        })

    return prompt | RunnableLambda(request, name='nvidia_chat')
