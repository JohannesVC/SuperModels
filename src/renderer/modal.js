import { SummaryAndMessages } from './common.js';

document.addEventListener('DOMContentLoaded', (event) => {
  const loadingIndicator = document.getElementById('loadingIndicator');
  const messagesDiv = document.getElementById('history-area');
  const selectButton = document.getElementById('select-button');
  const cancelButton = document.getElementById('cancel-button');

  window.api.runPythonScript(JSON.stringify({ load_master: true }));

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

  window.api.onPythonOutput((data) => {
    loadingIndicator.style.display = 'block';
    const chunk = JSON.parse(data);

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
                <button class="dropdownBtn text-left" data-target="messages-${sumMes.summary.id}">
                  <div class="text-right">
                    <i class="fas fa-chevron-down"></i>
                  </div>
                </button>
              </div>
              <div class="messages m-1" id="messages-${sumMes.summary.id}" style="display: none;">
              </div>`;

        messagesDiv.appendChild(newSummaryDiv)

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
      });
    }
    loadingIndicator.style.display = 'none';
    toggleSummary()
    toggleSelect()

    document.getElementById('searchInput').addEventListener('input', function () {
      filterMessages(this.value);
    });
  }, 'popup');

  function toggleSummary() {
    document.querySelectorAll('.dropdownBtn').forEach(button => {
      button.addEventListener('click', () => {
        const targetId = button.getAttribute('data-target');
        const targetElement = document.getElementById(targetId);
        targetElement.style.display = targetElement.style.display === 'none' ? 'block' : 'none'; // Toggle visibility
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
        }
      });
    });
  }

  if (selectButton) {
    selectButton.addEventListener('click', () => {
      if (summaryIds.length > 0) {
        console.log('summaryIds selected', summaryIds)

        window.api.runPythonScript(JSON.stringify({ summary_ids: summaryIds }));

        window.api.closePopup();
        summaryIds = [];
      } else {
        console.log("No summaries selected.");
      }
    });
  }
  if (cancelButton) {
    cancelButton.addEventListener('click', () => {
      // document.querySelectorAll('.summarySelect').forEach(summary => {
      //   summary.classList.remove('bg-neutral-700');
      // })
      summaryIds = [];
      window.api.closePopup();
    });
  }

  window.dropAll = () => {
    messagesDiv.innerHTML = '';
    window.api.runPythonScript(JSON.stringify({ drop_all: true }));
  };

  function filterMessages(searchTerm) {
    const messages = messagesDiv.querySelectorAll('.messages');

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