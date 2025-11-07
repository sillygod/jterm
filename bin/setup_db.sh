#!/bin/bash
# Database setup script for Web Terminal
# Creates default user and initializes database

set -e

DB_FILE="webterminal.db"

echo "🔧 Setting up Web Terminal database..."

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "❌ Database file not found: $DB_FILE"
    echo "📝 Please run migrations first: alembic upgrade head"
    exit 1
fi

# Create default user if not exists
echo "👤 Creating default user..."
sqlite3 "$DB_FILE" <<EOF
INSERT OR IGNORE INTO user_profiles (
    user_id, username, email, display_name, preferences,
    default_shell, keyboard_shortcuts, ai_settings, recording_settings,
    privacy_settings, storage_quota, storage_used, created_at,
    last_login_at, is_active, extra_metadata
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'default',
    'default@localhost',
    'Default User',
    '{}',
    'bash',
    '{}',
    '{}',
    '{}',
    '{}',
    1073741824,
    0,
    datetime('now'),
    datetime('now'),
    1,
    '{}'
);
EOF

# Verify user exists
USER_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM user_profiles WHERE user_id = '00000000-0000-0000-0000-000000000001';")

if [ "$USER_COUNT" -eq 1 ]; then
    echo "✅ Default user created successfully"
else
    echo "ℹ️  Default user already exists"
fi

# Show database info
echo ""
echo "📊 Database Statistics:"
echo "  Users: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM user_profiles;")"
echo "  Sessions: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM terminal_sessions;")"
echo "  Recordings: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM recordings;")"

echo ""
echo "✅ Database setup complete!"
echo ""
echo "🚀 You can now start the application:"
echo "   uvicorn src.main:app --reload"
