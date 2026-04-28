-- Migration 004: Fix practice name mismatches in app_user.practices[]
-- The values in practices[] must exactly match location.parent_org for the
-- assignee filter to work. These names drifted due to manual entry.

UPDATE discharge_app.app_user
SET practices = array_replace(
    array_replace(practices,
        'Dr. Jason R. Laney, PC',        'Laney Internal Medicine Group'),
        'Russell G. O''Neal, M.D. LLC',  'Russell G O''Neal, LLC')
WHERE user_email = 'bgraham@citadelhealth.com';

UPDATE discharge_app.app_user
SET practices = array_replace(
    array_replace(
    array_replace(practices,
        'Cumberland Womens Health Center', 'Cumberland Women''s Health Center'),
        'HP Internal Medicine, LLC',       'HP Internal Medicine'),
        'Northeast Family Practice, PC',   'Northeast Family Practice')
WHERE user_email = 'kjones3@citadelhealth.com';

UPDATE discharge_app.app_user
SET practices = array_replace(practices,
    'HP Internal Medicine, LLC', 'HP Internal Medicine')
WHERE user_email = 'rcruz@citadelhealth.com';

UPDATE discharge_app.app_user
SET practices = array_replace(
    array_replace(practices,
        'Internal Medicine Associates of Waycross', 'Waycross Internal Medicine'),
        'Smith-Lambert Clinic, P.C.',               'Smith Lambert Family Practice')
WHERE user_email = 'snelson@citadelhealth.com';
