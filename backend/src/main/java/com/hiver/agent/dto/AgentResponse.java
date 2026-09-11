package com.hiver.agent.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class AgentResponse {
    private String intent;
    private double intentConfidence;
    private String draftReply;
    private boolean shouldEscalate;
    private String escalationReason;
    private List<Map<String, Object>> retrievedExamples;
    private String modelVersion;
}