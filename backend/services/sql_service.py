from datetime import datetime

# Pure SQL DB helper functions (insert/fetch messages, chats)


from sql_connection import get_db_connection


def test_connection():
    """
    Test SQL Server connection and return version string if successful.
    """
    try:
        conn = get_db_connection()
        if not conn:
            raise Exception("Failed to connect to SQL Server")

        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION AS version")
        version = cursor.fetchone()[0]
        conn.close()
        return version

    except Exception as e:
        print("SQL error in test_connection:", e)
        return None


def create_chat(user):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO active_chats ([user]) OUTPUT INSERTED.chat_id VALUES (?)", (user,)
    )
    new_chat_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return new_chat_id


def insert_message(chat_id, user, message):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Get next message_id
    cursor.execute(
        "SELECT ISNULL(MAX(message_id),0)+1 FROM messages WHERE chat_id=?", (chat_id,)
    )
    next_id = cursor.fetchone()[0]

    # 2. Insert message
    cursor.execute(
        """
        INSERT INTO messages (chat_id, message_id, [user], message)
        OUTPUT inserted.created_at
        VALUES (?, ?, ?, ?)
        """,
        (chat_id, next_id, user, message),
    )

    # 3. Fetch created_at from OUTPUT clause
    created_at = cursor.fetchone()[0]

    # 4. Update last_updated for the chat
    cursor.execute(
        "UPDATE active_chats SET last_updated = GETDATE() WHERE chat_id=?", (chat_id,)
    )

    conn.commit()
    conn.close()

    # Return both id + timestamp
    return next_id, created_at


def get_messages(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [user], message, created_at FROM messages WHERE chat_id=? ORDER BY message_id ASC",
        (chat_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_active_chats():
    """
    Fetch all active chats from the database.
    Returns a list of tuples (chat_id, user, last_updated).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT chat_id, [user], last_updated FROM active_chats ORDER BY last_updated DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print("SQL error in get_active_chats:", e)
        return []


def get_last_x_messages(chat_id: int, x: int):
    """
    Fetch the last X messages for a given chat_id.
    Returns a list of dicts (JSON-serializable), ordered from oldest to newest.
    """
    try:
        conn = get_db_connection()
        if not conn:
            raise Exception("Database connection failed")

        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP {int(x)} [user], message, created_at, message_id
            FROM messages
            WHERE chat_id = ?
            ORDER BY created_at DESC
        """,
            (chat_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert to list of dicts (and reverse for natural order)
        messages = []
        for row in rows[::-1]:  # reverse to get chronological order
            user, message, created_at, message_id = row
            if isinstance(created_at, datetime):
                created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(
                {"user": user, "message": message, "created_at": created_at, "message_id": message_id}
            )

        return messages

    except Exception as e:
        print("SQL error in get_last_x_messages:", e)
        return []
    
def get_last_x_user_messages(chat_id: int, x: int, user: str):
    """
    Fetch the last X messages for a given chat_id from a specific user.
    Returns a list of dicts (JSON-serializable), ordered from oldest to newest.
    """
    try:
        conn = get_db_connection()
        if not conn:
            raise Exception("Database connection failed")

        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP {int(x)} [user], message, created_at
            FROM messages
            WHERE chat_id = ? AND [user] = ?
            ORDER BY created_at DESC
        """,
            (chat_id, user),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert to list of dicts (and reverse for natural order)
        messages = []
        for row in rows[::-1]:  # reverse to get chronological order
            user, message, created_at = row
            if isinstance(created_at, datetime):
                created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(
                {"user": user, "message": message, "created_at": created_at}
            )

        return messages

    except Exception as e:
        print("SQL error in get_last_x_user_messages:", e)
        return []

def set_starting_context_message_id(message_id, chat_id):
    """
    Sets the starting message ID for the current rolling topic summary for a given chat_id.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE active_chats
            SET current_context_start_message_id = ?
            WHERE chat_id = ?
            """,
            (message_id, chat_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("SQL error in set_starting_topic_summary_message_id:", e)
        if conn: 
            conn.close()
        return False

def set_current_context_summary(chat_id, new_summary):
    """
    Updates or sets the current rolling topic summary for a given chat_id.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE active_chats
            SET current_context_summary = ?
            WHERE chat_id = ?
            """,
            (new_summary, chat_id),
        )
        conn.commit()
        conn.close()
        return new_summary
    except Exception as e:
        print("SQL error in set_current_context_summary:", e)
        if conn: 
            conn.close()
        return []

def get_count_since_last_context_summary(chat_id):
    """
    Counts the number of messages since the last context summary for a given chat_id.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Get starting message ID for current context summary
        cursor.execute(
            """
            SELECT current_context_start_message_id
            FROM active_chats
            WHERE chat_id = ?
            """,
            (chat_id,),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 0  # No chat found

        start_message_id = row[0]

        # 2. Count messages since that ID
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM messages
            WHERE chat_id = ? AND message_id >= ?
            """,
            (chat_id, start_message_id),
        )
        count_row = cursor.fetchone()
        conn.close()

        if not count_row:
            return 0

        message_count = count_row[0]
        return message_count

    except Exception as e:
        print("SQL error in get_count_since_last_context_summary:", e)
        if conn:
            conn.close()
        return 0
    
    
def get_current_context_summary(chat_id):
    """
    Retrieves the current rolling topic summary for a given chat_id.
    Returns None if not found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT current_context_summary
            FROM active_chats
            WHERE chat_id = ?
            """,
            (chat_id,),  # NOTE: must be a tuple (chat_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        current_summary = row[0]
        return current_summary

    except Exception as e:
        print("SQL error in get_current_context_summary:", e)
        if conn:
            conn.close()
        return None
    
def get_message_timestamp(chat_id, message_id):
    """
    Retrieves the created_at timestamp for a specific message in a chat.
    Returns None if not found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT created_at
            FROM messages
            WHERE chat_id = ? AND message_id = ?
            """,
            (chat_id, message_id),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        created_at = row[0]
        return created_at

    except Exception as e:
        print("SQL error in get_message_timestamp:", e)
        if conn:
            conn.close()
        return None
    
def get_last_message_id(chat_id) -> int:
    """
    Retrieves the last message_id for a given chat_id.
    Returns None if no messages found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT MAX(message_id)
            FROM messages
            WHERE chat_id = ?
            """,
            (chat_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row or row[0] is None:
            return None

        last_message_id = row[0]
        return last_message_id

    except Exception as e:
        print("SQL error in get_last_message_id:", e)
        if conn:
            conn.close()
        return None
