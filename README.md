# Is it worth using "thinking mode" for local evaluation of AI models?

Today I tested the capabilities of Qwen3.8 with Q6_K_L quantization, as well as the difference in evaluation with "thinking mode" enabled and disabled.

Prompt objective: create an animated Rubik's Cube in the terminal using Python and built-in libraries.

For each attempt, I used three prompts to achieve the desired result.

In the upper terminal, "thinking mode" is enabled. The generation took a total of 1.5 hours at a speed of approximately 11 tok/sec. Overall, about 60,000 tokens were used.

In the lower terminal, the attempt was made with "thinking mode" disabled. The generation took about 10 minutes at a speed of approximately 13 tok/sec. Overall, about 8,000 tokens were used.

<img width="1451" height="1593" alt="failed_cube" src="https://github.com/user-attachments/assets/fdb8170a-39e1-4966-9555-a0e9344e0294" />
# rubic_cube_by_Qwen3_8
