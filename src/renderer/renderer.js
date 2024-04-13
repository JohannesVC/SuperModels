import { Summary, Message, SummaryAndMessages } from './common.js';
// console.log('Renderer loaded');

let allMessages = [];

document.addEventListener('DOMContentLoaded', (event) => {
  const loadingIndicator = document.getElementById('loadingIndicator');
  const sendButton = document.getElementById('send-button');
  const promptInput = document.getElementById('prompt-input');
  const inputArea = document.getElementById('input-area')
  const chatDiv = document.getElementById('chat');
  const messagesDiv = document.getElementById('message-area');
  const scrollArea = document.getElementById('scroll-area');
  const reloadConversations = document.getElementById('reload-conversations')
  let isStreaming = false;

  // textarea input formatting
  promptInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
  });

  function showLoader() {
    loadingIndicator.style.display = 'block';
    sendButton.querySelector('i').className = 'fas fa-regular fa-stop';
    sendButton.addEventListener('click', function () {
      window.api.onPythonExit(() => {
        console.log("Python stream interrupted.");
      });
      loadingIndicator.style.display = 'none';
      sendButton.querySelector('i').className = 'fas fa-arrow-right';
    });
  }

  let ModelName = 'SuperModel'
  let ModelType = 'mixtral'

  // send logic on button press: including runPythonScript
  function sendInput(inputElement) {
    console.log('sending input with', ModelName, ModelType)
    const prompt = inputElement.value.trim();
    if (prompt) {
      inputElement.value = '';
      inputElement.style.height = 'auto';      
      showLoader()
      // let promptMessage = {role: 'user', content: prompt}
      allMessages.push({ role: 'user', content: prompt });
      console.log('This is allMessages:', allMessages)
      const newMessage = document.createElement('div');
      newMessage.className = "messages"
      newMessage.innerHTML = `<div class="bg-neutral-700 rounded-lg p-3"><p><b>User</b></p>${window.api.markdown(prompt)}</div>`;
      messagesDiv.insertBefore(newMessage, chatDiv);
      scrollArea.scrollTop = scrollArea.scrollHeight;
      codeBlock(newMessage)
      window.api.runPythonScript(JSON.stringify({ prompt: prompt, model_name: [ModelName, ModelType] }));
    }
  }

  // enter as button press
  if (promptInput && sendButton) {
    promptInput.addEventListener('keypress', function (event) {      
      if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !isStreaming) {
        event.preventDefault();
        sendInput(this); // `this` refers to `promptInput` here
      }
    });
    sendButton.addEventListener('click', function () {
      console.log('click')
      if (!isStreaming) {
        sendInput(promptInput);
      }
    });
  } else {
    console.log('promptinput or sendbutton are not found in the DOM')
  }
  
  // output text: streaming from onPythonOutput
  let accumulatedText = '';
  let accumulatedData = '';
  const uniqueKeys = new Set();

  window.api.onPythonOutput((data) => {
    isStreaming = true;
    accumulatedData += data;
    const lines = accumulatedData.split('\n');
    accumulatedData = lines.pop();
    lines.forEach((line) => {
      if (line) {
        try {
          const chunk = JSON.parse(line);
          Object.keys(chunk).forEach(key => uniqueKeys.add(key));
          if (chunk.data || chunk.reflection || chunk.alt_stream || chunk.result || chunk.code) {
            window.dispatchEvent(new CustomEvent('openai-chunk', { detail: chunk }));
            accumulatedText += (chunk.data || "") + (chunk.reflection || "") + (chunk.result || "") + (chunk.alt_stream || "") + (chunk.code || "");  // + (chunk.stream || "");

            const renderedMarkdown = window.api.markdown(accumulatedText);
            chatDiv.innerHTML = `<div class="p-3"><p><b>Assistant</b></p>${renderedMarkdown}</div>`;
            codeBlock(chatDiv)
            scrollArea.scrollTop = scrollArea.scrollHeight;
          }
          // Check for end-of-stream indicator
          if (chunk.hasOwnProperty('end_of_stream')) {
            console.debug('Stream ended');
            if (accumulatedText) {
              const newMessage = document.createElement('div');
              newMessage.className = "messages p-3";
              newMessage.innerHTML = `<p><b>Assistant</b></p>` + window.api.markdown(accumulatedText);

              messagesDiv.insertBefore(newMessage, chatDiv);
              codeBlock(newMessage)
              allMessages.push({ role: 'assistant', content: accumulatedText });

              // scrollArea.scrollTop = scrollArea.scrollHeight;
            }
            chatDiv.innerHTML = '';
            accumulatedData = '';
            accumulatedText = '';
            isStreaming = false;
            loadingIndicator.style.display = 'none';
            sendButton.querySelector('i').className = 'fas fa-arrow-right';
          }

          ifLoadMaster(chunk)

          ifLoadHistory(chunk)

          scrollArea.scrollTop = scrollArea.scrollHeight;
        } catch (error) {
          console.error("Failed to parse chunk as JSON:", error);
        }
      }
    });
  });

  const keysArray = Array.from(uniqueKeys);
  console.log("Keys in renderer:", keysArray);

  function codeBlock(parentNode) {
    parentNode.querySelectorAll('pre code').forEach((block) => {
      const matches = block.className.match(/language-(\w+)/);
      if (matches) {
        const languageName = matches[1];
        const header = document.createElement('div');
        header.className = 'prose bg-neutral-700 rounded-t-lg p-2 text-sm';
        header.textContent = languageName;

        const parent = block.parentNode;
        parent.insertBefore(header, block);
      } else {
        // console.log("No language class found for:", block);
      }
    });
  }

  const dropdownBtn = document.getElementById('dropdownBtn');
  const dropdownContent = document.getElementById('dropdownContent');
  
  // Toggle dropdown
  dropdownBtn.addEventListener('click', () => {
    if (dropdownContent.classList.contains('hidden')) {
      dropdownContent.classList.remove('hidden');
      dropdownContent.classList.add('flex');
    } else {
      dropdownContent.classList.add('hidden');
      dropdownContent.classList.remove('flex');
    }
  });

  // Function to select a model and update the button text
  window.selectModel = (modelName) => {
    console.log('selected model:', modelName)
    document.getElementById('currentModel').textContent = modelName;
    ModelName = modelName
    dropdownContent.classList.add('hidden');
    dropdownContent.classList.remove('flex');
  };

  // Close dropdown when clicking outside
  window.addEventListener('click', (e) => {
    if (!dropdownBtn.contains(e.target)) {
      dropdownContent.classList.add('hidden');
      dropdownContent.classList.remove('flex');
    }
    if (!settingsBtn.contains(e.target)) {
      settingsContent.classList.add('hidden');
      settingsContent.classList.remove('flex');
      settingsBtn.classList.remove('bg-neutral-700')
    }
  });

  const settingsBtn = document.getElementById('settingsBtn');
  const settingsContent = document.getElementById('settingsContent');

  settingsBtn.addEventListener('click', () => {
    if (settingsContent.classList.contains('hidden')) {
      settingsContent.classList.remove('hidden');
      settingsContent.classList.add('flex');
      settingsBtn.classList.add('bg-neutral-700')
    } else {
      settingsContent.classList.add('hidden');
      settingsContent.classList.remove('flex');
      settingsBtn.classList.remove('bg-neutral-700')
    }
  });

  // Function to select a model and update the button text
  window.selectType = (modelType) => {
    const buttons = document.querySelectorAll('#settingsContent button');
    ModelType = modelType
    // Remove 'active' class from all buttons
    buttons.forEach(btn => {
      btn.classList.remove('bg-neutral-800');
    });
    const selectedButton = document.getElementById(modelType);
    if (selectedButton) {
      selectedButton.classList.add('bg-neutral-800');
    }
    // Hide the settings content as previously
    const settingsContent = document.getElementById('settingsContent');
    settingsContent.classList.add('hidden'); // Close the dropdown
    settingsContent.classList.remove('flex');
  };

  window.dropTable = () => {
    messagesDiv.querySelectorAll('.messages').forEach((messDiv) => {
      messDiv.outerHTML = '';
    });
    allMessages = [];
    window.api.runPythonScript(JSON.stringify({ drop_table: true }));
  };

  window.loadHistory = () => {
    reloadConversations.classList.add('flex');
    reloadConversations.classList.remove('hidden');
    inputArea.classList.add('hidden');
    inputArea.classList.remove('flex');
    if (!historyDiv.querySelectorAll('div').length > 0) {
      window.api.runPythonScript(JSON.stringify({ load_master: true }));
    }
    toggleSummary()
    toggleSelect() 
  }

  document.addEventListener('click', (event) => {
    if (event.target.tagName === 'A' && event.target.getAttribute('href').startsWith('http')) {
      event.preventDefault(); // Prevent default navigation
      window.api.openExternal(event.target.href);
    }
  });


  // modal
  ///////////////////////////////////////////////////////////////////////////

  const historyDiv = document.getElementById('history-area');
  const selectButton = document.getElementById('select-button');
  const cancelButton = document.getElementById('cancel-button');


  function ifLoadMaster(chunk) {
    if (chunk.hasOwnProperty('load_master')) {
      const data = chunk.load_master
      data.forEach((item) => {
        const sumMes = new SummaryAndMessages(item);
        const newSummaryDiv = document.createElement('div');
        newSummaryDiv.className = "summary";
        newSummaryDiv.innerHTML = `
              <div class="summarySelect m-1 rounded-lg p-2" data-target="summary-${sumMes.summary.id}" id="summary-${sumMes.summary.id}" title="Click for detail">
                  <h2>${sumMes.summary.title}</h2>
                  <p>${sumMes.summary.summary}</p>
                <button class="sumDropdownBtn text-left" data-target="messages-${sumMes.summary.id}">
                  <div class="text-right">
                    <i class="fas fa-chevron-down"></i>
                  </div>
                </button>
              </div>
              <div class="messages m-1" id="messages-${sumMes.summary.id}" style="display: none;">
              </div>`;

        historyDiv.appendChild(newSummaryDiv)

        const messagesContainer = document.getElementById(`messages-${sumMes.summary.id}`);

        sumMes.messages.forEach(message => {
          const newMessage = document.createElement('div');
          newMessage.className = "messages"
          if (message.role === "user") {
            newMessage.innerHTML = `<div class="bg-neutral-700 rounded-lg p-3"><p><b>User</b></p><div class="mess">${window.api.markdown(message.content)}</div></div>`;
            // console.log('User html:', content) 
          } else if (message.role === "assistant") {
            newMessage.innerHTML = `<div class="p-3"><p><b>Assistant</b></p><div class="mess">${window.api.markdown(message.content)}</div></div>`;
          }
          messagesContainer.appendChild(newMessage)
          codeBlock(newMessage)          
        });
        scrollArea.scrollTop = scrollArea.scrollHeight;
      });
    }
    toggleSummary()
    toggleSelect()    
    document.getElementById('searchInput').addEventListener('input', function () {
      filterMessages(this.value);
    });
    loadingIndicator.style.display = 'none';
    isStreaming = false
  }

  function ifLoadHistory(chunk) {
    if (chunk.hasOwnProperty('load_history')) {
      console.log('load_history received')
      const data = chunk.load_history
      data.forEach((item) => {
        const newMessage = document.createElement('div');
        newMessage.className = "messages p-3"
        if (item.role === "user") {
          newMessage.className = "messages p-3 bg-neutral-700 rounded-lg"
          newMessage.innerHTML = `<p><b>User</b></p>` + window.api.markdown(item.content);
        } else if (item.role === "assistant") {
          newMessage.className = "messages p-3"
          newMessage.innerHTML = `<p><b>Assistant</b></p>` + window.api.markdown(item.content);
        }
        messagesDiv.insertBefore(newMessage, chatDiv);
        codeBlock(newMessage)
        
      });
    }
    isStreaming = false
  }

  function toggleSummary() {
    document.querySelectorAll('.sumDropdownBtn').forEach(button => {
      button.addEventListener('click', () => {
        const targetId = button.getAttribute('data-target');
        const targetElement = document.getElementById(targetId);
        targetElement.style.display = targetElement.style.display === 'none' ? 'block' : 'none'; // Toggle visibility
        console.log('toggling sumDropdownBtn', targetElement.style.display)
      });
    });
  }

  let summaryIds = [];

  function toggleSelect() {
    document.querySelectorAll('.summarySelect').forEach(summary => {
      summary.addEventListener('click', () => {
        const match = summary.id.match(/summary-(\d+)/); // this is interesting: when looping over the elements, the id is available in dot notation
        if (match) {
          const summaryId = match[1]
          const isSelected = summary.classList.contains('bg-neutral-700');

          if (isSelected) {
            summaryIds = summaryIds.filter(id => id !== summaryId); // we filter the ids
            summary.classList.remove('bg-neutral-700');
          } else {
            summaryIds.push(summaryId);  // we add ids to an array
            summary.classList.add('bg-neutral-700');
          }
          console.log('summary.classList', summary.classList)
        }
      });
    });
  }

  if (selectButton) {
    selectButton.addEventListener('click', () => {
      if (summaryIds.length > 0) {
        console.log('summaryIds selected', summaryIds)

        window.api.runPythonScript(JSON.stringify({ summary_ids: summaryIds }));

        reloadConversations.classList.add('hidden');
        reloadConversations.classList.remove('flex');
        inputArea.classList.add('flex');
        inputArea.classList.remove('hidden');
        summaryIds = [];
        
      } else {
        console.log("No summaries selected.");
      }
    });
  }
  if (cancelButton) {
    cancelButton.addEventListener('click', () => {  
      reloadConversations.classList.add('hidden');
      reloadConversations.classList.remove('flex');
      inputArea.classList.add('flex');
      inputArea.classList.remove('hidden');
      summaryIds = [];
    });
  }

  window.dropAll = () => {
    historyDiv.innerHTML = '';
    window.api.runPythonScript(JSON.stringify({ drop_all: true }));
  };

  function filterMessages(searchTerm) {
    const messages = historyDiv.querySelectorAll('.messages');
    messages.forEach(messageElement => {
      messageElement.style.display = 'block';
      messageElement.querySelectorAll('.mess').forEach(mess => {
        let originalContent = mess.getAttribute('data-original-content');
        if (!originalContent) {
          originalContent = mess.textContent || ''; // Fallback to textContent or an empty string
          mess.setAttribute('data-original-content', originalContent);
        }

        if (searchTerm.trim()) {
          let highlightedContent = '';
          if (!searchTerm.trim()) {
            highlightedContent = originalContent;
          }
          const regex = new RegExp(`(${searchTerm})`, 'gi'); // 'g' for global, 'i' for case-insensitive

          highlightedContent = originalContent.replace(regex, `<span class="bg-yellow-400 text-black">$1</span>`);
          mess.innerHTML = highlightedContent;
          messageElement.style.display = highlightedContent.includes('<span class="bg-yellow-400 text-black">') ? '' : 'none';

        } else {
          mess.innerHTML = originalContent;
        }
      });
    });
  }

  // housekeeping
  window.api.onPythonError((event, error) => {
    console.info('Python:', error);
  });
  window.api.onPythonExit((event, code) => {
    console.info(`Python process exited with code ${code}`);
  });

});