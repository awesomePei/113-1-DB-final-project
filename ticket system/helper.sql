create or replace function Create_Study_Group(
    content TEXT,
    user_max BIGINT,
    course_id BIGINT,
    Owner_id BIGINT,
    event_date DATE,
    event_period_start INTEGER,
    event_duration BIGINT,
    classroom_id BIGINT
) returns BIGINT
as $$
declare
    new_event_id BIGINT;
BEGIN
    -- 使用 nextval 來從序列中獲取下個可用的 event_id
    new_event_id := nextval('study_event_event_id_seq');  -- 確保使用正確的序列名稱

    -- 插入到 STUDY_EVENT，並使用自動生成的 event_id
    INSERT INTO "STUDY_EVENT" (Event_id, Content, Status, User_max, Course_id, Owner_id)
    VALUES (new_event_id, content, 'Ongoing', user_max, course_id, owner_id);
    
    -- 插入 STUDY_EVENT_PERIOD
    for i in 0..(event_duration-1)
    loop
        INSERT INTO "STUDY_EVENT_PERIOD" (Event_date, Event_period, Classroom_id, Event_id)
        VALUES (event_date, event_period_start+i, classroom_id, new_event_id);
    end loop;
    
    return new_event_id;
END;
$$ LANGUAGE plpgsql;
