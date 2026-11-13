SELECT
    candidate_method,
    status,
    COUNT(*) AS count,
    ROUND(AVG(final_score)::NUMERIC, 4) AS avg_final_score,
    ROUND(MIN(final_score)::NUMERIC, 4) AS min_final_score,
    ROUND(MAX(final_score)::NUMERIC, 4) AS max_final_score
FROM {{ ref('stg_twitch_igdb_mapping_candidates') }}
GROUP BY candidate_method, status
ORDER BY candidate_method, status