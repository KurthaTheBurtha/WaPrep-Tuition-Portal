-- View all users in the database
SELECT 
    id,
    user_id,
    email,
    first_name,
    last_name,
    user_type,
    is_active,
    is_superuser,
    is_staff,
    date_joined,
    last_login
FROM tuition_user 
ORDER BY date_joined DESC;

-- Count users by type
SELECT 
    user_type,
    COUNT(*) as count,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_count
FROM tuition_user 
GROUP BY user_type;

-- Show only superusers
SELECT 
    id,
    user_id,
    email,
    first_name,
    last_name,
    is_active,
    date_joined
FROM tuition_user 
WHERE is_superuser = true
ORDER BY date_joined DESC; 