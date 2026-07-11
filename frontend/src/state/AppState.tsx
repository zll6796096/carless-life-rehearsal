/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

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
  selectedDestinationIds: string[] | null,
  profile: MobilityProfile | null,
  homeText: string
): DemoFixture {
  const selected =
    selectedDestinationIds === null
      ? fixture.destinations
      : fixture.destinations.filter((destination) => selectedDestinationIds.includes(destination.id));

  return {
    ...fixture,
    home_location: {
      ...fixture.home_location,
      name: homeText.trim() || fixture.home_location.name,
      address: fixture.home_location.address
    },
    destinations: selected,
    default_mobility_profile: profile ?? fixture.default_mobility_profile
  };
}

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [fixture, setFixture] = useState<DemoFixture | null>(null);
  const [diagnosis, setDiagnosis] = useState<LifeDiagnosis | null>(null);
  const [rehearsalTasks, setRehearsalTasks] = useState<RehearsalTask[]>([]);
  const [selectedDestinationIds, setSelectedDestinationIds] = useState<string[] | null>(null);
  const [profile, setProfile] = useState<MobilityProfile | null>(null);
  const [homeText, setHomeText] = useState("");
  const fixtureRequestRef = useRef<Promise<DemoFixture> | null>(null);
  const diagnosisRequestRef = useRef<Promise<LifeDiagnosis> | null>(null);
  const rehearsalRequestRef = useRef<Promise<RehearsalTask[]> | null>(null);

  const ensureFixture = useCallback(async () => {
    if (fixture) return fixture;
    if (fixtureRequestRef.current) return fixtureRequestRef.current;
    const request = getDemoFixture()
      .then((loaded) => {
        setFixture(loaded);
        setSelectedDestinationIds((current) =>
          current ?? loaded.destinations.map((destination) => destination.id)
        );
        setProfile((current) => current ?? loaded.default_mobility_profile);
        setHomeText((current) => current || loaded.home_location.name);
        return loaded;
      })
      .finally(() => {
        if (fixtureRequestRef.current === request) fixtureRequestRef.current = null;
      });
    fixtureRequestRef.current = request;
    return request;
  }, [fixture]);

  const ensureDiagnosis = useCallback(async () => {
    if (diagnosis) return diagnosis;
    if (diagnosisRequestRef.current) return diagnosisRequestRef.current;
    const request = ensureFixture()
      .then((loadedFixture) =>
        runDiagnosis(selectedFixture(loadedFixture, selectedDestinationIds, profile, homeText))
      )
      .then((response) => {
        setDiagnosis(response);
        return response;
      })
      .finally(() => {
        if (diagnosisRequestRef.current === request) diagnosisRequestRef.current = null;
      });
    diagnosisRequestRef.current = request;
    return request;
  }, [diagnosis, ensureFixture, homeText, profile, selectedDestinationIds]);

  const ensureRehearsals = useCallback(async () => {
    if (rehearsalTasks.length) return rehearsalTasks;
    if (rehearsalRequestRef.current) return rehearsalRequestRef.current;
    const request = ensureDiagnosis()
      .then(generateRehearsals)
      .then((response) => {
        setRehearsalTasks(response.tasks);
        return response.tasks;
      })
      .finally(() => {
        if (rehearsalRequestRef.current === request) rehearsalRequestRef.current = null;
      });
    rehearsalRequestRef.current = request;
    return request;
  }, [ensureDiagnosis, rehearsalTasks]);

  const toggleDestination = useCallback((destination: Destination) => {
    setSelectedDestinationIds((current) =>
      (current ?? []).includes(destination.id)
        ? (current ?? []).filter((id) => id !== destination.id)
        : [...(current ?? []), destination.id]
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
      selectedDestinationIds: selectedDestinationIds ?? [],
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
