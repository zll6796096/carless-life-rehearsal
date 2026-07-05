/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { generateRehearsals, getDemoFixture, runDiagnosis } from "../services/api";
import type { DemoFixture, Destination, LifeDiagnosis, MobilityProfile, RehearsalTask } from "../types";

type AppStateContextValue = {
  fixture: DemoFixture | null;
  diagnosis: LifeDiagnosis | null;
  rehearsalTasks: RehearsalTask[];
  selectedDestinationIds: string[];
  profile: MobilityProfile | null;
  homeText: string;
  setHomeText: (value: string) => void;
  toggleDestination: (destination: Destination) => void;
  setWalkMinutes: (minutes: number) => void;
  setMaxTransfers: (count: number) => void;
  ensureFixture: () => Promise<DemoFixture>;
  ensureDiagnosis: () => Promise<LifeDiagnosis>;
  ensureRehearsals: () => Promise<RehearsalTask[]>;
  setDiagnosis: (diagnosis: LifeDiagnosis) => void;
};

const AppStateContext = createContext<AppStateContextValue | null>(null);

function selectedFixture(
  fixture: DemoFixture,
  selectedDestinationIds: string[],
  profile: MobilityProfile | null,
  homeText: string
): DemoFixture {
  const selected = selectedDestinationIds.length
    ? fixture.destinations.filter((destination) => selectedDestinationIds.includes(destination.id))
    : fixture.destinations;

  return {
    ...fixture,
    home_location: {
      ...fixture.home_location,
      address: homeText.trim() || fixture.home_location.address
    },
    destinations: selected,
    default_mobility_profile: profile ?? fixture.default_mobility_profile
  };
}

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [fixture, setFixture] = useState<DemoFixture | null>(null);
  const [diagnosis, setDiagnosis] = useState<LifeDiagnosis | null>(null);
  const [rehearsalTasks, setRehearsalTasks] = useState<RehearsalTask[]>([]);
  const [selectedDestinationIds, setSelectedDestinationIds] = useState<string[]>([]);
  const [profile, setProfile] = useState<MobilityProfile | null>(null);
  const [homeText, setHomeText] = useState("");

  const ensureFixture = useCallback(async () => {
    if (fixture) return fixture;
    const loaded = await getDemoFixture();
    setFixture(loaded);
    setSelectedDestinationIds(loaded.destinations.map((destination) => destination.id));
    setProfile(loaded.default_mobility_profile);
    setHomeText(loaded.home_location.address);
    return loaded;
  }, [fixture]);

  const ensureDiagnosis = useCallback(async () => {
    if (diagnosis) return diagnosis;
    const loadedFixture = await ensureFixture();
    const response = await runDiagnosis(
      selectedFixture(loadedFixture, selectedDestinationIds, profile, homeText)
    );
    setDiagnosis(response);
    return response;
  }, [diagnosis, ensureFixture, homeText, profile, selectedDestinationIds]);

  const ensureRehearsals = useCallback(async () => {
    if (rehearsalTasks.length) return rehearsalTasks;
    const loadedDiagnosis = await ensureDiagnosis();
    const response = await generateRehearsals(loadedDiagnosis);
    setRehearsalTasks(response.tasks);
    return response.tasks;
  }, [ensureDiagnosis, rehearsalTasks]);

  const toggleDestination = useCallback((destination: Destination) => {
    setSelectedDestinationIds((current) =>
      current.includes(destination.id)
        ? current.filter((id) => id !== destination.id)
        : [...current, destination.id]
    );
    setDiagnosis(null);
    setRehearsalTasks([]);
  }, []);

  const setWalkMinutes = useCallback((minutes: number) => {
    setProfile((current) => ({
      ...(current ?? {
        walk_minutes: 10,
        max_transfers: 1,
        max_wait_minutes: 15,
        avoid_stairs: true,
        can_use_demand_transit: false,
        prefers_voice_guidance: true
      }),
      walk_minutes: minutes
    }));
    setDiagnosis(null);
    setRehearsalTasks([]);
  }, []);

  const setMaxTransfers = useCallback((count: number) => {
    setProfile((current) => ({
      ...(current ?? {
        walk_minutes: 10,
        max_transfers: 1,
        max_wait_minutes: 15,
        avoid_stairs: true,
        can_use_demand_transit: false,
        prefers_voice_guidance: true
      }),
      max_transfers: count
    }));
    setDiagnosis(null);
    setRehearsalTasks([]);
  }, []);

  const value = useMemo(
    () => ({
      fixture,
      diagnosis,
      rehearsalTasks,
      selectedDestinationIds,
      profile,
      homeText,
      setHomeText,
      toggleDestination,
      setWalkMinutes,
      setMaxTransfers,
      ensureFixture,
      ensureDiagnosis,
      ensureRehearsals,
      setDiagnosis
    }),
    [
      diagnosis,
      ensureDiagnosis,
      ensureFixture,
      ensureRehearsals,
      fixture,
      homeText,
      profile,
      rehearsalTasks,
      selectedDestinationIds,
      setMaxTransfers,
      setWalkMinutes,
      toggleDestination
    ]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error("useAppState must be used inside AppStateProvider");
  }
  return context;
}
