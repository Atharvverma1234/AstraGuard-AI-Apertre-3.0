import { useCallback, useRef, useEffect } from 'react';

export const useSoundEffects = () => {
    const audioContextRef = useRef<AudioContext | null>(null);

    useEffect(() => {
        // Initialize AudioContext on first user interaction or mount
        // Usually best to do lazy init to handle autoplay policies, but for this hook we set up ref
        if (typeof window !== 'undefined') {
            const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
            audioContextRef.current = new AudioContext();
        }
    }, []);

    const playTone = (freq: number, type: OscillatorType, duration: number, volume: number = 0.1) => {
        if (!audioContextRef.current) return;
        const ctx = audioContextRef.current;

        // Resume if suspended (common browser policy)
        if (ctx.state === 'suspended') ctx.resume();

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = type;
        osc.frequency.setValueAtTime(freq, ctx.currentTime);

        gain.gain.setValueAtTime(volume, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start();
        osc.stop(ctx.currentTime + duration);
    };

    const playClick = useCallback(() => {
        // High pitched "chirp" for UI interaction
        playTone(1200, 'sine', 0.1, 0.05);
        setTimeout(() => playTone(2000, 'triangle', 0.05, 0.02), 50);
    }, []);

    const playAlert = useCallback((severity: 'low' | 'high' = 'high') => {
        // Warning beep
        if (severity === 'high') {
            playTone(880, 'square', 0.2, 0.1);
            setTimeout(() => playTone(660, 'square', 0.2, 0.1), 200);
        } else {
            playTone(440, 'sine', 0.3, 0.05);
        }
    }, []);

    const playKeystroke = useCallback(() => {
        // Soft mechanical click
        playTone(600, 'triangle', 0.03, 0.02);
    }, []);

    const playSuccess = useCallback(() => {
        // Ascending chime
        playTone(500, 'sine', 0.2, 0.05);
        setTimeout(() => playTone(1000, 'sine', 0.4, 0.05), 100);
    }, []);

    return { playClick, playAlert, playKeystroke, playSuccess };
};
