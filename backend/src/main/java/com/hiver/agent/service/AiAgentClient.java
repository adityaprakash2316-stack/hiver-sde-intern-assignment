package com.hiver.agent.service;

import com.hiver.agent.dto.AiServiceResponse;
import com.hiver.agent.dto.MessageRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Service
public class AiAgentClient {

    private final WebClient webClient;

    public AiAgentClient(@Value("${ai.service.base-url:http://localhost:8000}") String baseUrl) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .build();
    }

    public AiServiceResponse handle(MessageRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("text", request.getText());
        if (request.getConversationHistory() != null) {
            body.put("conversation_history", request.getConversationHistory());
        }

        try {
            return webClient.post()
                    .uri("/v1/agent/handle")
                    .bodyValue(body)
                    .retrieve()
                    .bodyToMono(AiServiceResponse.class)
                    .timeout(Duration.ofSeconds(15))
                    .block();
        } catch (WebClientResponseException e) {
            throw new RuntimeException("AI service error: " + e.getStatusCode() + " - " + e.getResponseBodyAsString(), e);
        } catch (Exception e) {
            throw new RuntimeException("Failed to reach AI service: " + e.getMessage(), e);
        }
    }

    public Mono<Map> health() {
        return webClient.get()
                .uri("/health")
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(Duration.ofSeconds(5));
    }
}