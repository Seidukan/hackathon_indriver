import React, { useState, useRef, useEffect } from "react";
import logo from "./logo.png";

export default function App() {
  const [file, setFile] = useState(null);
  const [latA, setLatA] = useState("");
  const [lonA, setLonA] = useState("");
  const [latB, setLatB] = useState("");
  const [lonB, setLonB] = useState("");
  const [apiResponse, setApiResponse] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const mapInitialized = useRef(false);

  const handleNext = () => {
    setApiResponse(null);
    setIsLoading(false);
  };

  const handleCalculate = async () => {
    const payload = {
      src_lng: parseFloat(lonA),
      src_lat: parseFloat(latA),
      dst_lng: parseFloat(lonB),
      dst_lat: parseFloat(latB),
    };

    setIsLoading(true);
    setError(null);
    setApiResponse(null);

    try {
      const response = await fetch("https://1dd77389effe.ngrok-free.app/route", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      console.log("data", JSON.stringify(payload))
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setApiResponse(data);
      console.log("API Response:", data); // Log response for debugging
    } catch (error) {
      console.error("Error sending POST request:", error);
      setError("Failed to calculate. Please try again.");
    } finally {
      setIsLoading(false);
    }
    // const data = {
    //   "base": 300.0,
    //   "rate": 150.0,
    //   "demand": 0.8,
    //   "distance": 1200.5,
    //   "congestion": 0.6,
    // }
    // setApiResponse(data)
    // setIsLoading(false);
  };

  const calculatePrice = ({ base, demand, rate, distance, congestion }) => {
    return Math.round(base + demand + ((rate * distance * 0.001) * (1 + congestion)));
  };

  // Map initialization
  useEffect(() => {
    if (window.DG && mapRef.current && !mapInitialized.current) {
      window.DG.then(function () {
        const map = window.DG.map(mapRef.current, {
          center: [51.095, 71.4], // Astana
          zoom: 12,
        });
        mapInstance.current = map;
        mapInitialized.current = true;
        return () => {
          if (map) map.remove();
          mapInitialized.current = false;
        };
      }).catch((error) => {
        console.error("Error loading 2GIS DG API:", error);
      });
    } else if (!window.DG) {
      console.warn("2GIS DG API not loaded.");
    }
  }, []);

  return (
    <div className="min-h-screen relative" style={{ overflow: "hidden" }}>
      {/* Map as Interactive Background */}
      <div
        ref={mapRef}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          zIndex: 0,
        }}
      />

      {/* Overlay Content */}
      <div
        className="absolute inset-0 z-1"
        style={{ pointerEvents: "none" }}
      >
        <div className="flex flex-col items-center p-6">
          {/* Logo */}
          <img
            src={logo}
            className="w-40 mb-10"
            alt="InDrive Logo"
            style={{ pointerEvents: "none" }}
          />

          {/* Card */}
          <div
            className="w-full max-w-md bg-white bg-opacity-90 border border-gray-200 shadow-lg rounded-2xl p-8 space-y-8"
            style={{ pointerEvents: "none" }}
          >
            {/* <div className="flex flex-col items-center space-y-2">
              <input
                type="file"
                accept="text/csv"
                id="file-upload"
                onChange={handleFileUpload}
                className="mb-2 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                style={{ pointerEvents: "auto" }}
              />
              <label htmlFor="file-upload">
                <button
                  style={{ backgroundColor: "#C0F11C", pointerEvents: "auto" }}
                  onPointerOver={(e) => (e.currentTarget.style.backgroundColor = "#A3D317")}
                  onPointerOut={(e) => (e.currentTarget.style.backgroundColor = "#C0F11C")}
                  className="text-black font-semibold px-6 py-3 rounded-xl transition"
                >
                  {file ? `Uploaded: ${file.name}` : "Upload CSV File"}
                </button>
              </label>
            </div> */}

            {apiResponse ? (
              <div className="text-gray-800 space-y-2" style={{ pointerEvents: "auto" }}>
                <p>Formula: Price = Base + Demand + (Rate * Distance) * (1 + Congestion)</p>
                <p>Base = {apiResponse.base}</p>
                <p>Demand = {apiResponse.demand}</p>
                <p>Rate = {apiResponse.rate}</p>
                <p>Distance = {apiResponse.distance}</p>
                <p>Congestion = {apiResponse.congestion}</p>
                <p>Price = {calculatePrice(apiResponse)}</p>
              </div>
            ) : (
              <>
                {/* Point A Input */}
                <div className="w-full space-y-4">
                  <label className="block text-gray-700 font-medium mb-2">Point A</label>
                  <div className="flex space-x-4">
                    <input
                      type="text"
                      value={latA}
                      onChange={(e) => setLatA(e.target.value)}
                      placeholder="Latitude"
                      className="w-1/2 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      style={{ pointerEvents: "auto" }}
                    />
                    <input
                      type="text"
                      value={lonA}
                      onChange={(e) => setLonA(e.target.value)}
                      placeholder="Longitude"
                      className="w-1/2 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      style={{ pointerEvents: "auto" }}
                    />
                  </div>
                </div>

                {/* Point B Input */}
                <div className="w-full space-y-4">
                  <label className="block text-gray-700 font-medium mb-2">Point B</label>
                  <div className="flex space-x-4">
                    <input
                      type="text"
                      value={latB}
                      onChange={(e) => setLatB(e.target.value)}
                      placeholder="Latitude"
                      className="w-1/2 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      style={{ pointerEvents: "auto" }}
                    />
                    <input
                      type="text"
                      value={lonB}
                      onChange={(e) => setLonB(e.target.value)}
                      placeholder="Longitude"
                      className="w-1/2 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      style={{ pointerEvents: "auto" }}
                    />
                  </div>
                </div>
              </>
            )}

            {isLoading ? (
              <p className="text-gray-700 font-medium" style={{ pointerEvents: "auto" }}>Loading...</p>
            ) : error ? (
              <p className="text-red-500 font-medium" style={{ pointerEvents: "auto" }}>{error}</p>
            ) : null}

            {apiResponse ? (
            <div className="flex justify-center">
                <button
                  onClick={handleNext}
                  style={{ backgroundColor: "#C0F11C", pointerEvents: "auto" }}
                  onPointerOver={(e) => (e.currentTarget.style.backgroundColor = "#A3D317")}
                  onPointerOut={(e) => (e.currentTarget.style.backgroundColor = "#C0F11C")}
                  className="text-black font-semibold px-6 py-3 rounded-xl transition"
                >
                  Next
                </button>
              </div>
            ):(
              <div className="flex justify-center">
                <button
                  onClick={handleCalculate}
                  style={{ backgroundColor: "#C0F11C", pointerEvents: "auto" }}
                  onPointerOver={(e) => (e.currentTarget.style.backgroundColor = "#A3D317")}
                  onPointerOut={(e) => (e.currentTarget.style.backgroundColor = "#C0F11C")}
                  className="text-black font-semibold px-6 py-3 rounded-xl transition"
                >
                  Calculate
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}