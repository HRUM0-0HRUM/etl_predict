-- 1. Количество строк в основных таблицах (в каждой таблице характеристик должно быть столько же, сколько в phone)
SELECT 'phone' AS table_name, count(*) AS n FROM smartphones.phone
UNION ALL SELECT 'phone_model',        count(*) FROM smartphones.phone_model
UNION ALL SELECT 'phone_display',      count(*) FROM smartphones.phone_display
UNION ALL SELECT 'phone_body',         count(*) FROM smartphones.phone_body
UNION ALL SELECT 'phone_performance',  count(*) FROM smartphones.phone_performance
UNION ALL SELECT 'phone_camera_rear',  count(*) FROM smartphones.phone_camera_rear
UNION ALL SELECT 'phone_camera_front', count(*) FROM smartphones.phone_camera_front
UNION ALL SELECT 'phone_power',        count(*) FROM smartphones.phone_power
UNION ALL SELECT 'phone_connectivity', count(*) FROM smartphones.phone_connectivity
UNION ALL SELECT 'phone_features',     count(*) FROM smartphones.phone_features;

-- 2. Цена по брендам
SELECT b.name AS brand,
       count(*)                                        AS phones,
       round(avg(p.price))                             AS avg_price,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY p.price) AS median_price
FROM smartphones.phone p
JOIN smartphones.phone_model m ON m.model_id = p.model_id
JOIN smartphones.brand b       ON b.brand_id = m.brand_id
GROUP BY b.name
ORDER BY median_price DESC;

-- 3. Цена по линейкам процессоров
SELECT cf.name AS cpu_family,
       count(*)            AS phones,
       round(avg(p.price)) AS avg_price
FROM smartphones.phone p
JOIN smartphones.phone_performance pf ON pf.phone_id = p.phone_id
JOIN smartphones.cpu c                ON c.cpu_id = pf.cpu_id
JOIN smartphones.cpu_family cf        ON cf.cpu_family_id = c.cpu_family_id
GROUP BY cf.name
ORDER BY avg_price DESC;
