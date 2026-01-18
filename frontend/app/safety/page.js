'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import { Shield, AlertTriangle, Waves, Wind, Sun, Eye, Phone, Heart, Navigation, Zap } from 'lucide-react';

function SafetyContent() {
  const safetyCategories = [
    {
      id: 1,
      title: 'Beach Safety',
      icon: Waves,
      color: 'from-blue-500 to-cyan-500',
      tips: [
        'Always swim in designated areas with lifeguard supervision',
        'Check weather conditions and tide times before entering the water',
        'Never swim alone - use the buddy system',
        'Be aware of rip currents and know how to escape them',
      ]
    },
    {
      id: 2,
      title: 'Weather Awareness',
      icon: Wind,
      color: 'from-purple-500 to-pink-500',
      tips: [
        'Check local weather forecasts before heading to the beach',
        'Seek shelter immediately if you see lightning or hear thunder',
        'Be cautious of strong winds that can create dangerous surf conditions',
        'Monitor UV index and use appropriate sun protection',
      ]
    },
    {
      id: 3,
      title: 'Sun Protection',
      icon: Sun,
      color: 'from-yellow-500 to-orange-500',
      tips: [
        'Apply broad-spectrum sunscreen (SPF 30+) 30 minutes before sun exposure',
        'Reapply sunscreen every 2 hours and after swimming',
        'Wear protective clothing, hats, and UV-blocking sunglasses',
        'Seek shade during peak sun hours (10 AM - 4 PM)',
      ]
    },
    {
      id: 4,
      title: 'Marine Life',
      icon: Eye,
      color: 'from-green-500 to-emerald-500',
      tips: [
        'Do not touch or disturb marine life',
        'Shuffle your feet when walking in shallow water to avoid stingrays',
        'Stay calm if you encounter jellyfish - slowly back away',
        'Report any unusual marine life sightings to lifeguards',
      ]
    },
  ];

  const emergencyContacts = [
    { name: 'Emergency Services', number: '911', icon: Phone },
    { name: 'Coast Guard', number: '1-800-xxx-xxxx', icon: Shield },
    { name: 'Beach Patrol', number: '1-800-xxx-xxxx', icon: Navigation },
  ];

  return (
    <div className="p-4 lg:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Top Icons Bar */}
        <PageHeader />

        {/* Emergency Banner */}
        <div className="bg-gradient-to-r from-red-500 to-orange-600 rounded-2xl shadow-lg p-6 mb-8 text-white">
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-6 h-6 text-red-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-semibold mb-2">In Case of Emergency</h3>
              <p className="text-red-50 mb-4">
                If you or someone else is in immediate danger, call emergency services immediately. Don't wait.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {emergencyContacts.map((contact) => {
                  const Icon = contact.icon;
                  return (
                    <div key={contact.name} className="bg-white rounded-xl p-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Icon className="w-5 h-5 text-red-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">{contact.name}</p>
                          <p className="text-lg font-semibold text-gray-900">{contact.number}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Safety Categories */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {safetyCategories.map((category) => {
            const Icon = category.icon;
            return (
              <div key={category.id} className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                <div className={`bg-gradient-to-r ${category.color} p-6 text-white`}>
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center">
                      <Icon className="w-6 h-6 text-blue-600" />
                    </div>
                    <h3 className="text-xl font-semibold">{category.title}</h3>
                  </div>
                </div>
                <div className="p-6">
                  <ul className="space-y-3">
                    {category.tips.map((tip, index) => (
                      <li key={index} className="flex items-start space-x-3">
                        <div className="w-1.5 h-1.5 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
                        <span className="text-gray-700 text-sm">{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>

        {/* Rip Current Guide */}
        <div className="bg-gradient-to-br from-blue-600 to-cyan-700 rounded-2xl shadow-xl p-8 text-white mb-8">
          <div className="flex items-start space-x-4 mb-6">
            <div className="w-14 h-14 bg-white rounded-xl flex items-center justify-center flex-shrink-0">
              <Zap className="w-7 h-7 text-blue-600" />
            </div>
            <div>
              <h3 className="text-2xl font-semibold mb-2">How to Escape a Rip Current</h3>
              <p className="text-blue-50">Follow these steps if caught in a rip current</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl p-6">
              <div className="text-3xl font-semibold mb-2 text-[#0d4a6f]">1</div>
              <h4 className="font-semibold mb-2 text-gray-900">Stay Calm</h4>
              <p className="text-sm text-gray-600">Don't panic. Rip currents won't pull you under, just away from shore.</p>
            </div>
            <div className="bg-white rounded-xl p-6">
              <div className="text-3xl font-semibold mb-2 text-[#0d4a6f]">2</div>
              <h4 className="font-semibold mb-2 text-gray-900">Swim Parallel</h4>
              <p className="text-sm text-gray-600">Swim parallel to the shore until you're out of the current.</p>
            </div>
            <div className="bg-white rounded-xl p-6">
              <div className="text-3xl font-semibold mb-2 text-[#0d4a6f]">3</div>
              <h4 className="font-semibold mb-2 text-gray-900">Return to Shore</h4>
              <p className="text-sm text-gray-600">Once free, swim at an angle away from the current toward shore.</p>
            </div>
          </div>
        </div>

        {/* Additional Resources */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Heart className="w-5 h-5 mr-2 text-red-500" />
            Additional Safety Resources
          </h3>
          <div className="space-y-3">
            <a href="#" className="block p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
              <p className="font-medium text-gray-900">Download Safety Guide PDF</p>
              <p className="text-sm text-gray-600">Complete ocean safety handbook</p>
            </a>
            <a href="#" className="block p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
              <p className="font-medium text-gray-900">CPR & First Aid Training</p>
              <p className="text-sm text-gray-600">Find certified training courses near you</p>
            </a>
            <a href="#" className="block p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
              <p className="font-medium text-gray-900">Local Beach Conditions</p>
              <p className="text-sm text-gray-600">Real-time updates on beach safety</p>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SafetyPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <SafetyContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
