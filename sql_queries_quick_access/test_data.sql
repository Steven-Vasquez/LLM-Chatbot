-- Insert dummy active chats
INSERT INTO active_chats ([user])
VALUES 
('Alice'),
('Bob'),
('Charlie');

-- View inserted chats (optional)
SELECT * FROM active_chats;

-- Insert messages for each chat
-- Note: message_id is unique per chat (not an IDENTITY), so we must number them manually.

INSERT INTO messages (chat_id, message_id, [user], message)
VALUES
-- Chat 1 (Alice)
(1, 1, 'Alice', 'Hey, this is my first message!'),
(1, 2, 'Assistant', 'Hi Alice! How can I help you today?'),

-- Chat 2 (Bob)
(2, 1, 'Bob', 'Good morning! I need help with my account.'),
(2, 2, 'Assistant', 'Sure Bob, can you tell me more about the issue?'),

-- Chat 3 (Charlie)
(3, 1, 'Charlie', 'Just testing this chat app.'),
(3, 2, 'Assistant', 'Everything seems to be working fine!');

-- Verify all data
SELECT * FROM active_chats;
SELECT * FROM messages ORDER BY chat_id, message_id;
