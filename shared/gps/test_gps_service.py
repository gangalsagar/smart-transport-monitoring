import sys
import time

from shared.gps.gps_service import SharedGPSService


def main():
    print("=" * 60)
    print("SHARED GPS SERVICE TEST (WINDOWS LAPTOP LOCATION)")
    print("=" * 60)

    service = SharedGPSService(poll_interval_seconds=1.0)
    print(f"Active Provider : {service.active_provider_name}")
    print(f"Source Name     : {service.provider.source_name}")
    print("\nStarting SharedGPSService...")
    service.start()

    print("\nListening for live Windows Location updates (press Ctrl+C to stop)...")
    print("-" * 60)

    try:
        for i in range(1, 6):
            time.sleep(1.0)
            fix = service.get_latest_fix()
            print(
                f"[{i:02d}] Valid: {str(fix.valid):<5} | "
                f"Lat: {str(fix.latitude):<10} | "
                f"Lng: {str(fix.longitude):<10} | "
                f"Acc: {fix.accuracy_m:.1f}m | "
                f"Age: {fix.age_seconds:.1f}s | "
                f"Status: {fix.status} | "
                f"Source: {fix.source}"
            )
    except KeyboardInterrupt:
        print("\nStopping on user interrupt...")
    finally:
        service.stop()
        print("-" * 60)
        print("SharedGPSService stopped cleanly.")
        print("=" * 60)


if __name__ == "__main__":
    main()
