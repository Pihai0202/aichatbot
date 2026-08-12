package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

type Store struct {
	configPath   string
	sessionsPath string
}

func NewStore() *Store {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	dir := filepath.Join(home, ".config", "aichat-tui")
	_ = os.MkdirAll(dir, 0755)

	return &Store{
		configPath:   filepath.Join(dir, "config.json"),
		sessionsPath: filepath.Join(dir, "sessions.json"),
	}
}

func (s *Store) LoadConfig() Config {
	cfg := DefaultConfig()
	data, err := os.ReadFile(s.configPath)
	if err == nil {
		_ = json.Unmarshal(data, &cfg)
	}
	return cfg
}

func (s *Store) SaveConfig(cfg Config) error {
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.configPath, data, 0644)
}

func (s *Store) LoadSessions() ([]Session, error) {
	data, err := os.ReadFile(s.sessionsPath)
	if err != nil {
		return []Session{}, nil
	}
	var sessions []Session
	err = json.Unmarshal(data, &sessions)
	return sessions, err
}

func (s *Store) SaveSessions(sessions []Session) error {
	data, err := json.MarshalIndent(sessions, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.sessionsPath, data, 0644)
}

func NewSession(title string) Session {
	now := time.Now()
	return Session{
		ID:        now.Format("20060102_150405"),
		Title:     title,
		CreatedAt: now,
		UpdatedAt: now,
		Messages:  []Message{},
	}
}
