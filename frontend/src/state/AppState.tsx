/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

import { generateRehearsals, getDemoFixture, runDiagnosis } from "../services/api";
import type { DemoFixture, Destination, LifeDiagnosis, MobilityProfile, RehearsalTask, RehearsalRecord } from "../types";
import { departureError } from "../utils/departures";

type AppStateContextValue = {
  fixture: DemoFixture | null;
  diagnosis: LifeDiagnosis | null;
  rehearsalTasks: RehearsalTask[];
  rehearsalRecords: Record<string, RehearsalRecord>;
  recordRehearsal: (id: string, outcome: RehearsalRecord["outcome"], note: string) => void;
  selectedDestinationIds: string[];
  profile: MobilityProfile | null;
  homeText: string;
  outboundDeparture: string;
  returnDeparture: string;
  setDepartures: (outbound: string, returning: string) => void;
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
  const [rehearsalRecords, setRehearsalRecords] = useState<Record<string, RehearsalRecord>>({});
  const recordRehearsal = useCallback((id: string, outcome: RehearsalRecord["outcome"], note: string) => {
    if (!rehearsalTasks.some(task => task.id === id)) return;
    setRehearsalRecords(current => ({ ...current, [id]: { outcome, note: note.trim().slice(0, 500) } }));
  }, [rehearsalTasks]);
  const [selectedDestinationIds, setSelectedDestinationIds] = useState<string[] | null>(null);
  const [profile, setProfile] = useState<MobilityProfile | null>(null);
  const [homeText, updateHomeText] = useState("");
  const [outboundDeparture, updateOutbound] = useState("");
  const [returnDeparture, updateReturn] = useState("");
  const revisionRef = useRef(0);
  const fixtureRequestRef = useRef<Promise<DemoFixture> | null>(null);
  const diagnosisRequestRef = useRef<Promise<LifeDiagnosis> | null>(null);
  const rehearsalRequestRef = useRef<Promise<RehearsalTask[]> | null>(null);
  const rehearsalsLoadedRef = useRef(false);

  const invalidate = useCallback(() => {
    revisionRef.current += 1;
    diagnosisRequestRef.current = null;
    rehearsalRequestRef.current = null;
    rehearsalsLoadedRef.current = false;
    setDiagnosis(null);
    setRehearsalTasks([]);
    setRehearsalRecords({});
  }, []);
  const setHomeText = useCallback((value: string) => {
    updateHomeText(value);
    invalidate();
  }, [invalidate]);
  const setDepartures = useCallback((outbound: string, returning: string) => {
    updateOutbound(outbound);
    updateReturn(returning);
    invalidate();
  }, [invalidate]);

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
        updateHomeText((current) => current || loaded.home_location.name);
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
    const revision = revisionRef.current;
    const request = ensureFixture()
      .then((loadedFixture) => {
        const error = departureError(loadedFixture, outboundDeparture, returnDeparture);
        if (error) throw new Error(error);
        const payload = selectedFixture(loadedFixture, selectedDestinationIds, profile, homeText);
        if (!payload.destinations.length) throw new Error("目的地を選んでください。");
        if (loadedFixture.data_profile === "hakusan") {
          payload.home_location = loadedFixture.home_location;
          payload.outbound_departure = `${outboundDeparture}:00+09:00`;
          payload.return_departure = `${returnDeparture}:00+09:00`;
          payload.mock_transport_results = {};
        }
        return runDiagnosis(payload);
      })
      .then((response) => {
        if (revision !== revisionRef.current) throw new Error("入力が変更されました。");
        setDiagnosis(response);
        return response;
      })
      .finally(() => {
        if (diagnosisRequestRef.current === request) diagnosisRequestRef.current = null;
      });
    diagnosisRequestRef.current = request;
    return request;
  }, [diagnosis, ensureFixture, homeText, profile, selectedDestinationIds, outboundDeparture, returnDeparture]);

  const ensureRehearsals = useCallback(async () => {
    if (rehearsalsLoadedRef.current) return rehearsalTasks;
    if (rehearsalRequestRef.current) return rehearsalRequestRef.current;
    const revision = revisionRef.current;
    const request = ensureDiagnosis()
      .then(generateRehearsals)
      .then((response) => {
        if (revision !== revisionRef.current) throw new Error("入力が変更されました。");
        rehearsalsLoadedRef.current = true;
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
    invalidate();
  }, [invalidate]);

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
    invalidate();
  }, [invalidate]);

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
    invalidate();
  }, [invalidate]);

  const value = useMemo(
    () => ({
      fixture,
      diagnosis,
      rehearsalTasks,
      rehearsalRecords,
      recordRehearsal,
      selectedDestinationIds: selectedDestinationIds ?? [],
      profile,
      homeText,
      outboundDeparture,
      returnDeparture,
      setDepartures,
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
      outboundDeparture,
      returnDeparture,
      setDepartures,
      setHomeText,
      profile,
      rehearsalTasks,
      rehearsalRecords,
      recordRehearsal,
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
