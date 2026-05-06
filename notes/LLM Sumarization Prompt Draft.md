##### Short Message <6 word, ends with ?

**Infer intent of short message given recent chat history**

You are preparing text for vector embedding storage.



Given the chat context, infer the intended meaning of the latest message even if it's short or vague.

Write one factual sentence (<=15 words) summarizing its intent or meaning.



Context:

{recent\_context}



Latest message ({user}): "{message}"



Respond only with the summary text:





#### Default Message 6-25 word

**Simple factual summary of message meaning**

You are preparing text for vector embedding storage.



Write a concise, one sentence (10-20 words) factual summary describing the main idea or intent of the message.

Avoid filler or tone, focus on meaning only.



Message: "{message}"



Respond only with the summary text:





#### Long Message >25 word

**Summarize core content of long message**

You are preparing text for vector embedding storage.



The following message is long or detailed (like a story, explanation, or response).

Summarize its \*core content\* or main ideas clearly and concisely, within 1–2 short sentences (=30 words).

Avoid emotional tone or filler.



Message:

{message}



Respond only with the summary text:









#### 

