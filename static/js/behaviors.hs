/*
 * Hyperscript Behaviors for Web Terminal
 *
 * This file contains Hyperscript behaviors for interactive UI elements,
 * providing declarative event handling and DOM manipulation.
 */

/*******************************************************************************
 * TERMINAL BEHAVIORS
 ******************************************************************************/

-- Terminal focus behavior: automatically focus terminal on click
behavior terminalFocus
  on click
    call terminal.focus() on #xterm-container
  end
end

-- Terminal copy behavior: copy selected text to clipboard
behavior terminalCopy
  on click
    get terminal.getSelection() from #xterm-container
    call navigator.clipboard.writeText(result)
    add .copied to me
    wait 2s
    remove .copied from me
  end
end

-- Terminal paste behavior: paste from clipboard to terminal
behavior terminalPaste
  on click
    get navigator.clipboard.readText()
    send paste with detail: {text: result} to #xterm-container
  end
end

-- Terminal clear behavior: clear terminal screen
behavior terminalClear
  on click
    call terminal.clear() on #xterm-container
    send terminal-cleared to window
  end
end

-- Terminal resize behavior: fit terminal to container
behavior terminalResize
  on click or resize from window
    call fitAddon.fit() on #xterm-container
  end
end

/*******************************************************************************
 * THEME BEHAVIORS
 ******************************************************************************/

-- Theme preview behavior: show theme preview on hover
behavior themePreview
  on mouseenter
    get @data-theme-id from me
    fetch `/api/v1/themes/${result}/preview` as json
    put result into #theme-preview
  end
  on mouseleave
    put '' into #theme-preview
  end
end

-- Theme apply behavior: apply selected theme
behavior themeApply
  on click
    get @data-theme-id from me
    fetch `/api/v1/themes/${result}/apply` as json then
      add .active-theme to me
      remove .active-theme from .theme-card in closest .theme-list
      send theme-changed with detail: result to window
    end
  end
end

-- Theme export behavior: export theme configuration
behavior themeExport
  on click
    get @data-theme-id from me
    fetch `/api/v1/themes/${result}/export` then
      download result as `theme-${@data-theme-id}.json`
    end
  end
end

/*******************************************************************************
 * MEDIA BEHAVIORS
 ******************************************************************************/

-- Media viewer behavior: open media in viewer
behavior mediaView
  on click
    get @data-media-url from me
    put result into @src of #media-viewer-content
    add .visible to #media-viewer-modal
    send media-opened with detail: result to window
  end
end

-- Media fullscreen behavior: toggle fullscreen mode
behavior mediaFullscreen
  on click
    if #media-viewer-modal.classList.contains('fullscreen')
      remove .fullscreen from #media-viewer-modal
    else
      add .fullscreen to #media-viewer-modal
    end
  end
end

-- Media close behavior: close media viewer
behavior mediaClose
  on click or keydown[key=='Escape']
    remove .visible from #media-viewer-modal
    put '' into @src of #media-viewer-content
    send media-closed to window
  end
end

-- Media download behavior: download media file
behavior mediaDownload
  on click
    get @data-media-id from me
    fetch `/api/v1/media/${result}/content` then
      download result as @data-filename
    end
  end
end

/*******************************************************************************
 * RECORDING BEHAVIORS
 ******************************************************************************/

-- Recording start behavior: start session recording
behavior recordingStart
  on click
    fetch `/api/v1/recordings/${uuid()}/start`
      with method: 'POST'
      with body: JSON.stringify({sessionId: @data-session-id})
    then
      add .recording to #recording-indicator
      set @disabled to true on me
      remove @disabled from #recording-stop
      send recording-started to window
    end
  end
end

-- Recording stop behavior: stop session recording
behavior recordingStop
  on click
    get @data-recording-id from #recording-indicator
    fetch `/api/v1/recordings/${result}/stop`
      with method: 'POST'
    then
      remove .recording from #recording-indicator
      set @disabled to true on me
      remove @disabled from #recording-start
      send recording-stopped with detail: result to window
    end
  end
end

-- Recording playback behavior: play/pause recording
behavior recordingPlayback
  on click
    if window.recordingPlayer.isPlaying
      call window.recordingPlayer.pause()
      put 'Play' into me
      remove .playing from me
    else
      call window.recordingPlayer.play()
      put 'Pause' into me
      add .playing to me
    end
  end
end

-- Recording timeline behavior: seek to position
behavior recordingTimeline
  on input
    get my value
    call window.recordingPlayer.seek(result)
  end
end

-- Recording speed behavior: change playback speed
behavior recordingSpeed
  on change
    get my value
    call window.recordingPlayer.setSpeed(result)
    put `${result}x` into #speed-display
  end
end

/*******************************************************************************
 * AI ASSISTANT BEHAVIORS
 ******************************************************************************/

-- AI chat behavior: send message to AI
behavior aiChat
  on click or keydown[key=='Enter' and not shiftKey] from #ai-input
    if event.type == 'keydown' halt the event end

    get value of #ai-input
    if result is empty halt end

    -- Add user message to chat
    make a <div.ai-message.user/> called userMsg
    put result into userMsg
    put userMsg at end of #ai-chat-messages

    -- Clear input
    put '' into #ai-input

    -- Send to API
    fetch `/api/v1/ai/chat?sessionId=${@data-session-id}`
      with method: 'POST'
      with body: JSON.stringify({message: result})
    then
      -- Add AI response to chat
      make a <div.ai-message.assistant/> called aiMsg
      put result.response into aiMsg
      put aiMsg at end of #ai-chat-messages

      -- Scroll to bottom
      set #ai-chat-messages.scrollTop to #ai-chat-messages.scrollHeight

      send ai-response with detail: result to window
    end
  end
end

-- AI voice behavior: toggle voice input
behavior aiVoice
  on click
    if window.voiceInput.isListening
      call window.voiceInput.stop()
      remove .listening from me
      put 'Start Voice' into me
    else
      call window.voiceInput.start()
      add .listening to me
      put 'Stop Voice' into me
    end
  end
end

-- AI suggestion behavior: insert suggested command
behavior aiSuggestion
  on click
    get @data-command from me
    send input with detail: {data: result} to #xterm-container
    send suggestion-used with detail: result to window
  end
end

-- AI explain behavior: explain command output
behavior aiExplain
  on click
    get @data-command from me
    get @data-output from #terminal-output

    fetch `/api/v1/ai/explain?sessionId=${@data-session-id}`
      with method: 'POST'
      with body: JSON.stringify({command: @data-command, output: @data-output})
    then
      put result.explanation into #ai-explanation
      add .visible to #ai-explanation-modal
    end
  end
end

/*******************************************************************************
 * MODAL & DIALOG BEHAVIORS
 ******************************************************************************/

-- Modal open behavior
behavior modalOpen
  on click
    get @data-modal-target from me
    add .visible to ${result}
    add .modal-open to body
  end
end

-- Modal close behavior
behavior modalClose
  on click or keydown[key=='Escape'] from window
    if event.type == 'keydown' and not closest .modal.visible halt end
    remove .visible from closest .modal
    remove .modal-open from body
  end
end

-- Dropdown toggle behavior
behavior dropdownToggle
  on click
    toggle .open on closest .dropdown
  end

  on click from elsewhere
    if not I match .dropdown remove .open from me end
  end
end

/*******************************************************************************
 * FORM & INPUT BEHAVIORS
 ******************************************************************************/

-- Auto-save behavior: save input value on change
behavior autoSave
  on change or blur
    get my value
    get @data-save-key from me
    call localStorage.setItem(@data-save-key, my value)
    add .saved to me
    wait 1s
    remove .saved from me
  end

  on load
    get @data-save-key from me
    get localStorage.getItem(result)
    if result is not empty put result into my value end
  end
end

-- Character counter behavior: show remaining characters
behavior charCounter
  on input
    get my value.length
    get @maxlength from me
    put `${result} / ${@maxlength}` into #char-count

    if result >= @maxlength
      add .limit-reached to me
    else
      remove .limit-reached from me
    end
  end
end

-- Copy to clipboard behavior
behavior copyToClipboard
  on click
    get @data-copy-text from me or my textContent
    call navigator.clipboard.writeText(result)

    make a <span.copy-notification/> called notification
    put 'Copied!' into notification
    put notification before me

    wait 2s
    remove notification
  end
end

/*******************************************************************************
 * NOTIFICATION BEHAVIORS
 ******************************************************************************/

-- Toast notification behavior
behavior showToast
  on custom-event
    get @data-message from event.detail or event.detail

    make a <div.toast/> called toast
    put result into toast
    put toast at end of #toast-container

    wait 3s
    add .fade-out to toast
    wait 300ms
    remove toast
  end
end

-- Progress indicator behavior
behavior showProgress
  on htmx:beforeRequest
    add .loading to me
    put 'Loading...' into #progress-text
  end

  on htmx:afterRequest
    remove .loading from me
    put '' into #progress-text
  end
end

/*******************************************************************************
 * DRAG & DROP BEHAVIORS
 ******************************************************************************/

-- File upload drag & drop behavior
behavior fileDragDrop
  on dragover or dragenter
    halt the event
    add .drag-over to me
  end

  on dragleave or dragend
    remove .drag-over from me
  end

  on drop
    halt the event
    remove .drag-over from me

    get event.dataTransfer.files
    for file in result
      send file-dropped with detail: file to me
    end
  end
end

/*******************************************************************************
 * ACCESSIBILITY BEHAVIORS
 ******************************************************************************/

-- Keyboard navigation behavior
behavior keyboardNav
  on keydown[key=='ArrowDown']
    halt the event
    focus on next .focusable
  end

  on keydown[key=='ArrowUp']
    halt the event
    focus on previous .focusable
  end

  on keydown[key=='Home']
    halt the event
    focus on first .focusable
  end

  on keydown[key=='End']
    halt the event
    focus on last .focusable
  end
end

-- Focus trap behavior (for modals)
behavior focusTrap
  on keydown[key=='Tab']
    get the first .focusable in me
    get the last .focusable in me

    if event.shiftKey and document.activeElement == first
      halt the event
      focus on last
    else if not event.shiftKey and document.activeElement == last
      halt the event
      focus on first
    end
  end
end

/*******************************************************************************
 * ANIMATION BEHAVIORS
 ******************************************************************************/

-- Fade in behavior
behavior fadeIn
  on load or intersection
    add .fade-in to me
  end
end

-- Slide in behavior
behavior slideIn
  on load or intersection
    add .slide-in to me
  end
end

-- Pulse on change behavior
behavior pulseOnChange
  on htmx:afterSwap
    add .pulse to me
    wait 500ms
    remove .pulse from me
  end
end

/*******************************************************************************
 * UTILITY BEHAVIORS
 ******************************************************************************/

-- Confirm action behavior
behavior confirmAction
  on click
    get @data-confirm-message from me or 'Are you sure?'
    if not confirm(result) halt end
  end
end

-- Toggle class behavior
behavior toggleClass
  on click
    get @data-toggle-class from me
    toggle ${result} on @data-toggle-target or me
  end
end

-- Scroll to top behavior
behavior scrollToTop
  on click
    call window.scrollTo({top: 0, behavior: 'smooth'})
  end
end

-- External link behavior
behavior externalLink
  on click
    halt the event
    get @href from me
    call window.open(result, '_blank')
  end
end

/*******************************************************************************
 * SESSION BEHAVIORS
 ******************************************************************************/

-- Session heartbeat behavior
behavior sessionHeartbeat
  init
    repeat every 30s
      fetch `/api/v1/sessions/${@data-session-id}`
      if response.status == 404
        send session-expired to window
        halt the event
      end
    end
  end
end

-- Auto logout behavior
behavior autoLogout
  init
    set :idleTime to 0

    repeat every 1s
      increment :idleTime

      if :idleTime > 1800  -- 30 minutes
        send auto-logout to window
        halt the event
      end
    end
  end

  on mousemove or keydown from window
    set :idleTime to 0
  end
end

/*******************************************************************************
 * HELPER FUNCTIONS
 ******************************************************************************/

-- UUID generator
def uuid()
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  })
end

-- Download helper
def download(data, filename)
  make a <a/> called link
  set link.href to URL.createObjectURL(data)
  set link.download to filename
  call link.click()
  call URL.revokeObjectURL(link.href)
end
