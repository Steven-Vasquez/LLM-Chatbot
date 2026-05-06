CREATE TABLE active_chats (
    chat_id INT IDENTITY(1,1) PRIMARY KEY,
    [user] NVARCHAR(50) NOT NULL,
    current_context_summary_uuid UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    last_updated DATETIME DEFAULT GETDATE()
);

CREATE TABLE messages (
    chat_id INT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES active_chats(chat_id),
    message_id INT NOT NULL,
    [user] NVARCHAR(50) NOT NULL,
    message NVARCHAR(MAX) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    PRIMARY KEY (chat_id, message_id)
);