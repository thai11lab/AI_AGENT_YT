Role: Senior Python AI Engineer specializing in Streamlit Dashboards and LangGraph Streaming Architectures.

Task: Write a complete, production-ready `app_mission_control.py` using Streamlit that acts as the Mission Control UI for our Phase 1 `LangGraph` Adversarial Documentary System (v3.0).

Requirements:
1. MULTI-JOB QUEUE & SIDEBAR:
   - Sidebar with a `st.text_area` to input multiple competitor YouTube URLs (one per line), a `st.slider` for max concurrent threads, and a "Start Batch Processing" button.
   - Maintain job state in `st.session_state.jobs` tracking: current node, loop iteration count, FSS score, Delta_It novelty score, debate logs, and final MasterProductionScript JSON.

2. REAL-TIME ADVERSARIAL DEBATE STREAMING (TAB 1):
   - Top metric row using `st.metric` displaying: Competitor Hook WPM, Current FSS Score (target >= 8.5), Semantic Novelty Delta_It, and Estimated Script Cost.
   - Visual status pipeline showing the 6 nodes: Autopsy -> Architect -> Hunter -> Prosecutor -> Judge -> Showrunner.
   - Expandable "Courtroom Debate Feed" using `st.chat_message` with distinct avatars for:
     * Architect (o3): Displaying the 3 Counter-Hypotheses.
     * Hunter (Exa/Tavily/Firecrawl): Displaying scraped primary evidence and URLs.
     * Prosecutor (o3-mini): Highlighting rejected claims in red (`st.error`) and search directives, or approved claims in green (`st.success`).

3. INTERACTIVE SCENE-BY-SCENE EDITOR & SINGLE-SHOT REROLL (TAB 2):
   - Display the `StyleBible` in an editable `st.expander`.
   - Filter scenes by Act (Act 1 Hook vs Acts 2-5).
   - Render each Scene inside a structured container with columns:
     * Left column: Editable `voiceover_text` (`st.text_area`) and `audio_cues` tags.
     * Middle column: `visual_mode` selector (`AI_VIDEO_HIGH_COST` vs `STATIC_2.5D_PARALLAX`). Dynamically show `video_motion_prompt` if AI Video is selected, or the 3 Parallax layer inputs (`foreground`, `midground`, `background`) if Parallax is selected.
     * Right column: Deterministic Pydantic Validator badges (checking for digits `0-9`, banned AI words, and trigger_word presence) + a `[Reroll This Scene Only]` button that re-triggers only that specific scene's LLM call without regenerating the whole script.

4. EXPORT & JSON INSPECTOR (TAB 3):
   - Full JSON preview with a `st.download_button` to export `master_script_v3.json` formatted with Frame Index (`fps: 30`) ready for Stage 2 & Stage 3.

Include realistic mock state initialization so the Streamlit app can be previewed and tested immediately even before API keys are entered.