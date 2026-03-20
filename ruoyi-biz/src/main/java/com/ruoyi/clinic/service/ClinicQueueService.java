package com.ruoyi.clinic.service;

import com.ruoyi.clinic.config.QueueWebSocketHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Slf4j
@Service
@RequiredArgsConstructor
public class ClinicQueueService {

    private static final String QUEUE_KEY = "QUEUE:WAITING";

    private final StringRedisTemplate stringRedisTemplate;

    private final QueueWebSocketHandler queueWebSocketHandler;

    /**
     * Add a patient to the waiting queue (ZSET) using current timestamp as score
     *
     * @param patientName The name of the patient (e.g., "Elma", "Amy", "思想犯")
     */
    public void enqueue(String patientName) {
        // Use epoch milli as score for finer granularity than seconds
        long timestamp = Instant.now().toEpochMilli();
        stringRedisTemplate.opsForZSet().add(QUEUE_KEY, patientName, timestamp);
        log.info("Patient {} added to queue with timestamp score {}", patientName, timestamp);
    }

    /**
     * Call the next patient in the queue atomically and broadcast to screens
     *
     * @param roomNumber The room number assigned to the patient
     * @return The patient name called, or null if the queue is empty
     */
    public String callNext(String roomNumber) {
        // Atomic operation to pop the element with the minimum score (oldest timestamp)
        ZSetOperations.TypedTuple<String> tuple = stringRedisTemplate.opsForZSet().popMin(QUEUE_KEY);

        if (tuple != null && tuple.getValue() != null) {
            String patientName = tuple.getValue();
            log.info("Calling next patient {} to room {}", patientName, roomNumber);

            // Push event to all connected screens
            queueWebSocketHandler.broadcastCall(patientName, roomNumber);

            return patientName;
        } else {
            log.info("Queue is empty. No patient to call.");
            return null;
        }
    }
}
