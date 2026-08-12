package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/textarea"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type focusArea int

const (
	focusInput focusArea = iota
	focusSidebar
	focusViewport
	focusModal
)

type model struct {
	config      Config
	store       *Store
	client      *AIClient
	sessions    []Session
	activeIdx   int
	viewport    *viewport.Model
	textarea    *textarea.Model
	focus       focusArea
	width       int
	height      int
	isStreaming bool
	errStr      string
	statusMsg   string

	// Settings modal state
	showModal    bool
	modalFocus   int
	ollamaModels []string

	tokenChan chan string
	errChan   chan error
}

func initialModel() model {
	st := NewStore()
	cfg := st.LoadConfig()
	sessions, _ := st.LoadSessions()

	if len(sessions) == 0 {
		sessions = append(sessions, NewSession("New Conversation"))
		_ = st.SaveSessions(sessions)
	}

	ta := textarea.New()
	ta.Placeholder = "Type your prompt here... (Enter to send, Shift+Enter for newline)"
	ta.Focus()
	ta.Prompt = "┃ "
	ta.CharLimit = 8000
	ta.SetWidth(60)
	ta.SetHeight(3)
	ta.ShowLineNumbers = false

	vp := viewport.New(60, 20)
	vp.SetContent("Welcome to AI Chat TUI! Select model or start typing below.")

	m := model{
		config:      cfg,
		store:       st,
		client:      NewAIClient(),
		sessions:    sessions,
		activeIdx:   0,
		viewport:    &vp,
		textarea:    &ta,
		focus:       focusInput,
		statusMsg:   "Ready",
		tokenChan:   make(chan string, 100),
		errChan:     make(chan error, 1),
	}

	m.refreshViewport()
	return m
}

func (m model) Init() tea.Cmd {
	return textarea.Blink
}

func listenToStream(tokenChan chan string, errChan chan error) tea.Cmd {
	return func() tea.Msg {
		select {
		case token, ok := <-tokenChan:
			if !ok {
				return StreamDoneMsg{}
			}
			return TokenMsg(token)
		case err, ok := <-errChan:
			if ok && err != nil {
				return StreamErrMsg{Err: err}
			}
			return StreamDoneMsg{}
		}
	}
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.resizeLayout()

	case tea.KeyMsg:
		if m.showModal {
			return m.updateModal(msg)
		}

		switch {
		case key.Matches(msg, key.NewBinding(key.WithKeys("ctrl+c"))):
			return m, tea.Quit

		case key.Matches(msg, key.NewBinding(key.WithKeys("ctrl+q"))):
			return m, tea.Quit

		case key.Matches(msg, key.NewBinding(key.WithKeys("ctrl+n"))):
			// New Chat Session
			newSess := NewSession(fmt.Sprintf("Chat %d", len(m.sessions)+1))
			m.sessions = append([]Session{newSess}, m.sessions...)
			m.activeIdx = 0
			m.store.SaveSessions(m.sessions)
			m.refreshViewport()
			m.statusMsg = "Created new chat session"

		case key.Matches(msg, key.NewBinding(key.WithKeys("ctrl+s"))):
			// Open Settings / Model Selector
			m.showModal = true
			m.statusMsg = "Fetching local models..."
			go func() {
				models, _ := m.client.FetchOllamaModels(m.config.OllamaBaseURL)
				if len(models) > 0 {
					m.ollamaModels = models
				}
			}()

		case key.Matches(msg, key.NewBinding(key.WithKeys("tab"))):
			// Cycle panel focus
			if m.focus == focusInput {
				m.focus = focusSidebar
				m.textarea.Blur()
			} else if m.focus == focusSidebar {
				m.focus = focusViewport
			} else {
				m.focus = focusInput
				m.textarea.Focus()
			}

		case msg.String() == "enter" && m.focus == focusInput && !msg.Alt:
			if m.isStreaming {
				return m, nil
			}
			prompt := strings.TrimSpace(m.textarea.Value())
			if prompt == "" {
				return m, nil
			}

			// Add User Message
			m.textarea.Reset()
			sess := &m.sessions[m.activeIdx]
			if len(sess.Messages) == 0 {
				title := prompt
				if len(title) > 25 {
					title = title[:25] + "..."
				}
				sess.Title = title
			}

			sess.Messages = append(sess.Messages, Message{Role: "user", Content: prompt})
			sess.Messages = append(sess.Messages, Message{Role: "assistant", Content: ""})
			m.store.SaveSessions(m.sessions)

			m.isStreaming = true
			m.errStr = ""
			m.statusMsg = "Generating response..."
			m.refreshViewport()

			m.tokenChan = make(chan string, 100)
			m.errChan = make(chan error, 1)

			go m.client.StreamResponse(m.config, sess.Messages[:len(sess.Messages)-1], m.tokenChan, m.errChan)
			return m, listenToStream(m.tokenChan, m.errChan)

		case msg.String() == "up" || msg.String() == "k":
			if m.focus == focusSidebar {
				if m.activeIdx > 0 {
					m.activeIdx--
					m.refreshViewport()
				}
			}

		case msg.String() == "down" || msg.String() == "j":
			if m.focus == focusSidebar {
				if m.activeIdx < len(m.sessions)-1 {
					m.activeIdx++
					m.refreshViewport()
				}
			}
		}

	case TokenMsg:
		sess := &m.sessions[m.activeIdx]
		if len(sess.Messages) > 0 && sess.Messages[len(sess.Messages)-1].Role == "assistant" {
			sess.Messages[len(sess.Messages)-1].Content += string(msg)
		}
		m.refreshViewport()
		return m, listenToStream(m.tokenChan, m.errChan)

	case StreamDoneMsg:
		m.isStreaming = false
		m.statusMsg = "Response finished."
		m.store.SaveSessions(m.sessions)
		return m, nil

	case StreamErrMsg:
		m.isStreaming = false
		m.errStr = msg.Err.Error()
		m.statusMsg = "Error generating response"
		return m, nil
	}

	if m.focus == focusInput {
		newTa, cmd := m.textarea.Update(msg)
		m.textarea = &newTa
		cmds = append(cmds, cmd)
	} else if m.focus == focusViewport {
		newVp, cmd := m.viewport.Update(msg)
		m.viewport = &newVp
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

func (m *model) updateModal(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.showModal = false
	case "1":
		m.config.ActiveProvider = ProviderOllama
		m.store.SaveConfig(m.config)
		m.statusMsg = "Switched to Ollama Provider"
	case "2":
		m.config.ActiveProvider = ProviderOpenAI
		m.store.SaveConfig(m.config)
		m.statusMsg = "Switched to OpenAI Provider"
	case "down", "j":
		if len(m.ollamaModels) > 0 {
			m.modalFocus = (m.modalFocus + 1) % len(m.ollamaModels)
			m.config.OllamaModel = m.ollamaModels[m.modalFocus]
			m.store.SaveConfig(m.config)
		}
	}
	return m, nil
}

func (m *model) resizeLayout() {
	sidebarWidth := 28
	mainWidth := m.width - sidebarWidth - 3
	if mainWidth < 20 {
		mainWidth = 20
	}

	inputHeight := 5
	headerHeight := 3
	statusHeight := 1
	vpHeight := m.height - inputHeight - headerHeight - statusHeight - 2
	if vpHeight < 5 {
		vpHeight = 5
	}

	m.viewport.Width = mainWidth
	m.viewport.Height = vpHeight
	m.textarea.SetWidth(mainWidth)
}

func (m *model) refreshViewport() {
	if len(m.sessions) == 0 {
		m.viewport.SetContent("No conversation sessions.")
		return
	}
	sess := m.sessions[m.activeIdx]
	var sb strings.Builder

	userStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#00F0FF")).Bold(true)
	aiStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#A000FF")).Bold(true)
	userMsgStyle := lipgloss.NewStyle().Background(lipgloss.Color("#1A1B26")).Foreground(lipgloss.Color("#C0CAF5")).Padding(0, 1).MarginLeft(2)
	aiMsgStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E6ED")).Padding(0, 1)

	for _, msg := range sess.Messages {
		if msg.Role == "user" {
			sb.WriteString(userStyle.Render("👤 YOU:") + "\n")
			sb.WriteString(userMsgStyle.Render(msg.Content) + "\n\n")
		} else if msg.Role == "assistant" {
			sb.WriteString(aiStyle.Render("🤖 ASSISTANT:") + "\n")
			sb.WriteString(aiMsgStyle.Render(msg.Content) + "\n\n")
		}
	}

	if m.errStr != "" {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FF5555")).Bold(true)
		sb.WriteString(errStyle.Render("❌ Error: "+m.errStr) + "\n")
	}

	m.viewport.SetContent(sb.String())
	m.viewport.GotoBottom()
}

func (m model) View() string {
	if m.width == 0 || m.height == 0 {
		return "Initializing AI Chat TUI..."
	}

	if m.showModal {
		return m.renderModal()
	}

	// 1. Header
	providerTag := fmt.Sprintf("[%s : %s]", strings.ToUpper(string(m.config.ActiveProvider)), m.getCurrentModel())
	headerStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FFFFFF")).
		Background(lipgloss.Color("#5F00FF")).
		Padding(0, 1).
		Width(m.width)

	header := headerStyle.Render(fmt.Sprintf(" ⚡ AI CHAT TUI  │  %s  │  Session: %s", providerTag, m.sessions[m.activeIdx].Title))

	// 2. Sidebar
	sidebarWidth := 28
	sidebarStyle := lipgloss.NewStyle().
		Width(sidebarWidth).
		Height(m.height - 5).
		Border(lipgloss.NormalBorder(), false, true, false, false).
		BorderForeground(lipgloss.Color("#3B4252"))

	if m.focus == focusSidebar {
		sidebarStyle = sidebarStyle.BorderForeground(lipgloss.Color("#00F0FF"))
	}

	var sbLines []string
	sbLines = append(sbLines, lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#88C0D0")).Render("💬 SESSIONS (Ctrl+N)"))
	for i, s := range m.sessions {
		title := s.Title
		if len(title) > 20 {
			title = title[:17] + "..."
		}
		if i == m.activeIdx {
			sbLines = append(sbLines, lipgloss.NewStyle().Background(lipgloss.Color("#3B4252")).Foreground(lipgloss.Color("#E5E9F0")).Bold(true).Render("> "+title))
		} else {
			sbLines = append(sbLines, lipgloss.NewStyle().Foreground(lipgloss.Color("#4C566A")).Render("  "+title))
		}
	}
	sidebarContent := sidebarStyle.Render(strings.Join(sbLines, "\n"))

	// 3. Main Viewport & Input Box
	mainWidth := m.width - sidebarWidth - 4
	vpStyle := lipgloss.NewStyle().Width(mainWidth)
	if m.focus == focusViewport {
		vpStyle = vpStyle.Border(lipgloss.NormalBorder()).BorderForeground(lipgloss.Color("#00F0FF"))
	}
	vpView := vpStyle.Render(m.viewport.View())

	inputStyle := lipgloss.NewStyle().Width(mainWidth)
	if m.focus == focusInput {
		inputStyle = inputStyle.Border(lipgloss.RoundedBorder()).BorderForeground(lipgloss.Color("#5F00FF"))
	} else {
		inputStyle = inputStyle.Border(lipgloss.RoundedBorder()).BorderForeground(lipgloss.Color("#3B4252"))
	}
	inputView := inputStyle.Render(m.textarea.View())

	rightPanel := lipgloss.JoinVertical(lipgloss.Left, vpView, inputView)

	// 4. Combine Body
	body := lipgloss.JoinHorizontal(lipgloss.Top, sidebarContent, rightPanel)

	// 5. Status Bar
	statusStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#D8DEE9")).
		Background(lipgloss.Color("#2E3440")).
		Width(m.width)
	status := statusStyle.Render(fmt.Sprintf(" [Tab] Switch Focus | [Ctrl+N] New Session | [Ctrl+S] Model Settings | [Ctrl+Q] Quit | Status: %s", m.statusMsg))

	return lipgloss.JoinVertical(lipgloss.Left, header, body, status)
}

func (m model) getCurrentModel() string {
	if m.config.ActiveProvider == ProviderOllama {
		return m.config.OllamaModel
	}
	return m.config.OpenAIModel
}

func (m model) renderModal() string {
	modalStyle := lipgloss.NewStyle().
		Border(lipgloss.DoubleBorder()).
		BorderForeground(lipgloss.Color("#00F0FF")).
		Padding(1, 2).
		Width(60).
		Background(lipgloss.Color("#1E1E2E"))

	var sb strings.Builder
	sb.WriteString(lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00F0FF")).Render("⚙️ SETTINGS & MODEL SELECTOR") + "\n\n")
	sb.WriteString("Select Backend Provider:\n")
	if m.config.ActiveProvider == ProviderOllama {
		sb.WriteString("  [1] [X] Ollama (Local)  [2] [ ] OpenAI / Custom API\n\n")
	} else {
		sb.WriteString("  [1] [ ] Ollama (Local)  [2] [X] OpenAI / Custom API\n\n")
	}

	sb.WriteString("Available Ollama Local Models (Press Up/Down to choose):\n")
	if len(m.ollamaModels) == 0 {
		sb.WriteString("  (No local models detected or connecting...)\n")
	} else {
		for i, mod := range m.ollamaModels {
			if mod == m.config.OllamaModel {
				sb.WriteString(fmt.Sprintf("  > [%s] (Selected)\n", mod))
			} else {
				sb.WriteString(fmt.Sprintf("    %s\n", mod))
			}
			if i > 8 {
				break
			}
		}
	}

	sb.WriteString("\nPress [Esc] to Close Modal")
	return lipgloss.Place(m.width, m.height, lipgloss.Center, lipgloss.Center, modalStyle.Render(sb.String()))
}

func main() {
	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Error running TUI: %v\n", err)
		os.Exit(1)
	}
}
