import React, { useEffect, useState } from 'react';
import { OverviewCard } from '../../components/shared/OverviewCard';
import { UserGroupIcon, ClipboardDocumentListIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

export const Dashboard: React.FC = () => {
  const [kpis, setKpis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/analytics/dashboard`);
        setKpis(response.data);
      } catch (err: any) {
        console.error("Dashboard Load Error:", err.response?.status, err.response?.data);
        setError(err.response?.data?.detail || "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) return <div className="p-8 text-center animate-pulse">Gathering insights...</div>;
  if (error) return <div className="p-8 text-red-500 bg-red-50 rounded-lg m-4 border border-red-200">Error: {error}</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <OverviewCard 
          title="Total Patients" 
          value={kpis.total_patients} 
          trend={kpis.total_patients_trend} 
          icon={<UserGroupIcon className="h-6 w-6" />}
        />
        <OverviewCard 
          title="Referrals (30d)" 
          value={kpis.total_referrals_30d} 
          trend={kpis.total_referrals_trend} 
          icon={<ClipboardDocumentListIcon className="h-6 w-6" />}
        />
        {kpis.total_facilities && (
          <OverviewCard 
            title="Active Facilities" 
            value={kpis.total_facilities} 
            trend={0} // No trend for facility count usually
            icon={<BuildingOfficeIcon className="h-6 w-6" />}
          />
        )}
      </div>
      {/* Charts would go here */}
    </div>
  );
};