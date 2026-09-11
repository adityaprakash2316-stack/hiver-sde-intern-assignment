package com.hiver.agent.controller;

import com.hiver.agent.dto.AgentResponse;
import com.hiver.agent.dto.AiServiceResponse;
import com.hiver.agent.dto.MessageRequest;
import com.hiver.agent.service.AiAgentClient;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1")
@CrossOrigin(origins = "*")
public class AgentController {

    private final AiAgentClient aiClient;

    public AgentController(AiAgentClient aiClient) {
        this.aiClient = aiClient;
    }

    @PostMapping("/support")
    public ResponseEntity<AgentResponse> handleSupport(@Valid @RequestBody MessageRequest request) {
        AiServiceResponse aiResp = aiClient.handle(request);

        AgentResponse response = new AgentResponse();
        response.setIntent(aiResp.getIntent());
        response.setIntentConfidence(aiResp.getIntentConfidence());
        response.setDraftReply(aiResp.getDraftReply());
        response.setShouldEscalate(aiResp.isShouldEscalate());
        response.setEscalationReason(aiResp.getEscalationReason());
        response.setRetrievedExamples(aiResp.getRetrievedExamples());
        response.setModelVersion(aiResp.getModelVersion());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        try {
            Map aiHealth = aiClient.health().block();
            return ResponseEntity.ok(Map.of(
                    "backend", "UP",
                    "aiService", aiHealth != null ? aiHealth : "UNKNOWN"
            ));
        } catch (Exception e) {
            return ResponseEntity.ok(Map.of(
                    "backend", "UP",
                    "aiService", "DOWN",
                    "error", e.getMessage()
            ));
        }
    }

    @GetMapping("/intents")
    public ResponseEntity<?> intents() {
        return ResponseEntity.ok(Map.of(
                "intents", new String[]{
                        "battery_drain", "ios_update_issue", "app_crash", "icloud_sync",
                        "hardware_failure", "account_lock", "billing_refund", "app_store_purchase",
                        "wifi_connectivity", "performance_lag", "screen_issue", "feature_request",
                        "general_inquiry", "complaint_escalation"
                }
        ));
    }
}