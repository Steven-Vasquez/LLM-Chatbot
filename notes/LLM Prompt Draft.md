**SYSTEM INSTRUCTIONS:**

{system\_instructions}

*(preset, possibly dynamic options?)*



**SHORT-TERM CONTEXT (Messages):**

{recent\_messages}

*(last x messages from SQL DB, minus current message)*



**RETRIEVED\_CONTEXT (Messages + Summaries):**

{ranked\_and\_summarized\_context}

*Multi-stage retrieval.*

1. *Retrieve x semantically similar past messages from the Messages ChromaDB.*
2. *Retrieve y semantically similar past message chunk summaries from the Context\_Summaries ChromaDB, entries marked as complete (exclude the current ongoing topic summary).*

   * **For 1 and 2:**
     Use weighted average approach, higher weights to more recent messages

3. *Rank all according to cosine similarity or a reranker model's score (like bge-reranker).*
4. *Choose the top z ranked results, label as summary or message, and they will act as retrieved context.*



**CURRENT\_TOPIC\_SUMMARY:**

{current\_topic\_summary}

*On each user message,*

*If:*

* *More than x (15-20?) messages since last summary*
* *The topic has drifted (semantic similarity (cosine similarity?) < .75)*

  *- Use small window (5-10?) of last N messages to get weighted similarity over a recent window vs measuring drift of just 1 msg.*

   	- Skip if user is chatbot, message is very short (<4 words?), lexical cues suggesting continuation

* *(optional?) User hasn't messaged for > 1 hour*

  

  *Then: compute current topic summary embedding and save to Context\_Summaries ChromaDB, mark this topic\_summary as complete in and start a new topic window.*

  

  *Else: Update current\_topic\_summary if needed (incremental summarization), re-embed it, upsert (update/insert) into Context\_Summaries*

  

  **CURRENT USER MESSAGE:**

  {current\_user\_input}

  

  TASK:

  Respond to the user's message naturally and helpfully,

  using any relevant information from the context or recent conversation.

  If something is unclear, ask for clarification.

  

  When responding, prioritize:

  1\. SHORT-TERM CONTEXT for immediate continuity.

  2\. RETRIEVED\_CONTEXT for related prior discussions.

  3\. CURRENT\_TOPIC\_SUMMARY for maintaining thematic consistency.

  

  If any retrieved context seems inconsistent or outdated compared to recent messages, prefer the recent messages.

