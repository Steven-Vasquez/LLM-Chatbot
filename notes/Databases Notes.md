##### SQL DATABASE Tables

###### **messages**:

* chat\_id
* messages\_id
* user
* message
* created\_at
* PK: (chat\_id, message\_id)



###### **active\_chats**:

* chat\_id (PK)
* user
* current\_context\_start\_message\_id
* current\_context\_summary
* last\_updated



##### ChromaDB VECTOR DATABASE COLLECTIONS:

###### **messages**:

(Store embeddings for each individual chat message, summarized (conditionally context-aware summary))

\- Document = chat message

\- Embedding: calculated from chat message

\- ID = chat{chat\_id}\_msg{message\_id} from SQL DB

\- Metadata:

* chat\_id (from SQL messages tbl)
* message\_id (from SQL messages tbl)
* user (from SQL messages tbl)
* created\_at (from SQL messages tbl)



###### **context\_summaries**:

(Store embeddings for topic summaries/topic chunks)

\- Document = the generated context summary

\- Embedding = calculated from ongoing or finalized context summary text

\- ID = (temp) chat\_id\_\[generated uuid]

\- Metadata:

* chat\_id (from SQL messages tbl)
* ongoing: true/false
* start\_message\_id (from SQL messages tbl)
* end\_message\_id (from SQL messages tbl)
* OPTIONAL??:
* created\_at (timestamp)
* updated\_at (timestamp)
* version (incremental update version?)
* summary\_type (?)
