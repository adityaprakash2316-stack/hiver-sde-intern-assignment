package com.hiver.agent.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class AiServiceResponse {
    private String intent;
    private double intentConfidence;
    private String draftReply;
    private boolean shouldEscalate;
    private String escalationReason;
    private List<Map<String, Object>> retrievedExamples;
    private String modelVersion;
}