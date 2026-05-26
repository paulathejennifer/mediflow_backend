import React, { useEffect, useState } from 'react';
import { OverviewCard } from '../../components/shared/OverviewCard';
import { UserGroupIcon, ClipboardDocumentListIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline';
import { analyticsService, AnalyticsMetrics } from '../../src/features/analytics/services/analytics.service'; // Adjust path as needed

export const Dashboard: React.FC = () => {
  const [kpis, setKpis] = useState<AnalyticsMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await analyticsService.getDashboardKpis();
        setKpis(data);
      } catch (err: any) {
        console.error("Dashboard Load Error:", err.response?.status, err.response?.data);
        setError(err.response?.data?.detail || "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) return <div className="p-8 text-center animate-pulse text-muted-foreground">Gathering insights...</div>;
  if (error) return <div className="p-8 text-red-500 bg-red-50 rounded-lg m-4 border border-red-200">Error: {error}</div>;
  if (!kpis) return null; // Ensure kpis is not null before rendering

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <OverviewCard 
          title="Total Patients" 
          value={kpis.total_patients} 
          trend={kpis.totalPatientsTrend} 
          trendLabel="vs last month"
          icon={<UserGroupIcon className="h-6 w-6" />}
        />
        <OverviewCard 
          title="Referrals (30d)" 
          value={kpis.totalReferrals} 
          trend={kpis.totalReferralsTrend} 
          trendLabel="vs last month"
          icon={<ClipboardDocumentListIcon className="h-6 w-6" />}
        />
        <OverviewCard 
          title="Total Users" 
          value={kpis.totalUsers} 
          trend={kpis.totalUsersTrend} 
          trendLabel="vs last month"
          icon={<UserGroupIcon className="h-6 w-6" />}
        />
        <OverviewCard 
          title="Total Documents" 
          value={kpis.totalDocuments} 
          trend={kpis.totalDocumentsTrend} 
          trendLabel="vs last month"
          icon={<ClipboardDocumentListIcon className="h-6 w-6" />}
        />
        <OverviewCard 
          title="Total Facilities" 
          value={kpis.total_facilities || 0} 
          trend={0} // Facilities don't typically trend monthly
          trendLabel="vs last month"
          icon={<BuildingOfficeIcon className="h-6 w-6" />}
        />
      </div>
      {/* Charts would go here */}
    </div>
  );
};