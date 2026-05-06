CREATE TABLE active_chats (
    chat_id INT IDENTITY(1,1) PRIMARY KEY,
    [user] NVARCHAR(50) NOT NULL,
    last_updated DATETIME DEFAULT GETDATE(),
    current_context_start_message_id  INT DEFAULT 1,
    current_context_summary NVARCHAR(MAX) NULL
);

CREATE TABLE messages (
    message_id INT NOT NULL,
    [user] NVARCHAR(50) NOT NULL,
    message NVARCHAR(MAX) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    chat_id INT NOT NULL,
        FOREIGN KEY (chat_id) REFERENCES active_chats(chat_id),
    PRIMARY KEY (chat_id, message_id)
);