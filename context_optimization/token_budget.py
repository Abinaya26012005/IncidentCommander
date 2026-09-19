def budget(request,tokens):
    parts=[request.system_prompt_tokens,request.tool_definition_tokens,request.reserved_output_tokens,request.policy.safety_margin_tokens]
    if any(type(v) is not int or v<0 for v in parts):raise ValueError('Invalid token reservations')
    limit=request.model_context_limit
    if limit is not None and (type(limit) is not int or limit<=0):raise ValueError('Invalid context limit')
    available=None if limit is None else max(0,limit-sum(parts))
    fits=None if limit is None else tokens+sum(parts)<=limit
    return {'context_limit':limit,'system_tokens':parts[0],'tool_tokens':parts[1],'reserved_output_tokens':parts[2],'safety_margin':parts[3],'available_context_budget':available,'selected_context_tokens':tokens,'utilization_percentage':None if available is None else round(tokens/max(1,available)*100,1),'fits_context_budget':fits,'status':'NOT CONFIGURED' if limit is None else 'PASS' if fits else 'EXCEEDED'}
