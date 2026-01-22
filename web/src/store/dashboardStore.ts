import { create } from 'zustand';

interface DashboardState {
  timeRange: '1h' | '24h' | '7d' | '30d';
  selectedThreat: string | null;
  liveUpdatesEnabled: boolean;
  setTimeRange: (range: '1h' | '24h' | '7d' | '30d') => void;
  setSelectedThreat: (id: string | null) => void;
  toggleLiveUpdates: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  timeRange: '24h',
  selectedThreat: null,
  liveUpdatesEnabled: true,
  setTimeRange: (range) => set({ timeRange: range }),
  setSelectedThreat: (id) => set({ selectedThreat: id }),
  toggleLiveUpdates: () => set((state) => ({
    liveUpdatesEnabled: !state.liveUpdatesEnabled
  })),
}));