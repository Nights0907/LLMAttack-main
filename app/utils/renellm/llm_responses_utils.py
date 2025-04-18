from app.utils.llm_completion_utils import get_llm_responses, claudeCompletion

def gpt_responses(args, text: str):
    user_input = text
    user_message={"role": "user", "content": user_input}
    messages = [user_message]
    model_output = get_llm_responses(args.test_model,
                                  messages,
                                  args.temperature,
                                  args.retry_times,
                                  )
    return model_output

def claude_responses(args, text: str):
    user_input = text
    model_output = claudeCompletion(
                args.test_model,
                args.max_tokens,
                args.temperature,
                user_input,
                args.retry_times,
                args.round_sleep,
                args.fail_sleep,
                args.claude_api_key,
                args.claude_base_url)
    return model_output

def llama2_responses(args, text: str):
    pass

def mistral_responses(args, model, tokenizer, text: str):
    user_input = [
        {"role": "user", "content": text}
    ]
   

    encodeds = tokenizer.apply_chat_template(user_input, return_tensors="pt")
    model_inputs = encodeds.to("cuda")
    model.to("cuda")

    generated_ids = model.generate(model_inputs, pad_token_id=tokenizer.eos_token_id, max_new_tokens=args.max_tokens, do_sample=True)
    decoded = tokenizer.batch_decode(generated_ids)

    parts = decoded[0].split("[/INST] ")
    if len(parts) > 1:
        content_after_inst = parts[1]
    else:
        content_after_inst = ""
    model_output = content_after_inst.replace("</s>", "")

    return model_output
    



    pass
    