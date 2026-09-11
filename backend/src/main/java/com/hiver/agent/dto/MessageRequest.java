package com.hiver.agent.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

@Data
public class MessageRequest {
    @NotBlank(message = "text is required")
    @Size(max = 2000)
    private String text;

    private List<String> conversationHistory;
}
