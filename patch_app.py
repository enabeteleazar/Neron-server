import re

path = '/mnt/usb-storage/Neron_AI/modules/neron_core/app.py'

with open(path, 'r') as f:
    content = f.read()

# 1. Ajouter l'import
old_import = 'from orchestrator.intent_router import IntentRouter, Intent'
new_import = 'from orchestrator.intent_router import IntentRouter, Intent\nfrom agents.system_agent import handle_system_status'

if 'from agents.system_agent' not in content:
    content = content.replace(old_import, new_import)
    print("✅ Import ajouté")
else:
    print("⚠️  Import déjà présent")

# 2. Ajouter handler SYSTEM_STATUS dans /input/stream
old_stream = '''        intent_result = await router.route(query)
        if intent_result.intent == Intent.TIME_QUERY:
            response = _handle_time_query(intent_result, {}, 0, query).response
            yield f"data: {json.dumps({'token': response, 'done': True})}\\n\\n"
            return'''

new_stream = '''        intent_result = await router.route(query)

        if intent_result.intent == Intent.SYSTEM_STATUS:
            response = await handle_system_status(query)
            yield f"data: {json.dumps({'token': response, 'done': True})}\\n\\n"
            await _store_memory(query, response, {"intent": "system_status"})
            return

        if intent_result.intent == Intent.TIME_QUERY:
            response = _handle_time_query(intent_result, {}, 0, query).response
            yield f"data: {json.dumps({'token': response, 'done': True})}\\n\\n"
            return'''

if 'SYSTEM_STATUS' not in content:
    content = content.replace(old_stream, new_stream)
    print("✅ Handler SYSTEM_STATUS ajouté dans /input/stream")
else:
    print("⚠️  Handler déjà présent")

# 3. Ajouter handler dans /input/text
old_text = '''        if intent_result.intent == Intent.TIME_QUERY:
            core_response = _handle_time_query(intent_result, metadata, start, query)
        elif intent_result.intent == Intent.WEB_SEARCH:'''

new_text = '''        if intent_result.intent == Intent.SYSTEM_STATUS:
            response = await handle_system_status(query)
            execution_time_ms = round((time.monotonic() - start) * 1000, 2)
            await _store_memory(query, response, metadata)
            core_response = CoreResponse(
                response=response,
                intent="system_status",
                agent="system_agent",
                confidence="high",
                timestamp=utc_now_iso(),
                execution_time_ms=execution_time_ms,
                metadata=metadata
            )
        elif intent_result.intent == Intent.TIME_QUERY:
            core_response = _handle_time_query(intent_result, metadata, start, query)
        elif intent_result.intent == Intent.WEB_SEARCH:'''

if 'system_agent' not in content:
    content = content.replace(old_text, new_text)
    print("✅ Handler SYSTEM_STATUS ajouté dans /input/text")
else:
    print("⚠️  Handler déjà présent dans /input/text")

with open(path, 'w') as f:
    f.write(content)

print("\n✅ Patch terminé")
